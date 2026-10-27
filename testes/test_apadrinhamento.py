"""Fase 3, H7 e H8: apadrinhamento mensal e doacao com destino.

Criterios em docs/HISTORIAS-FASE-3.md.
"""

import asyncio
import itertools
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RegraNegocioError
from app.core.tempo import hoje_na_ong
from app.esquemas.apadrinhamento import ApadrinhamentoCriar
from app.esquemas.processo_adocao import ProcessoAdocaoAtualizarStatus
from app.modelos.adotante import Adotante
from app.modelos.apadrinhamento import Apadrinhamento
from app.modelos.enums import (
    EspeciePet,
    SituacaoAdocaoPet,
    StatusProcessoAdocao,
    StatusSaudePet,
)
from app.modelos.padrinho import Padrinho
from app.modelos.pet import Pet
from app.modelos.processo_adocao import ProcessoAdocao
from app.servicos import apadrinhamento as servico_apadrinhamento
from app.servicos import processo_adocao as servico_processo
from testes.conftest import FabricaSessaoTeste, esperar_conexoes_bloqueadas

HOJE = hoje_na_ong()
# So precisam ser unicos: o ORM nao confere os digitos verificadores.
_CPFS = (f"{n:011d}" for n in itertools.count(10_000_000_000))


async def _padrinho(sessao: AsyncSession, nome: str = "Joana") -> Padrinho:
    padrinho = Padrinho(nome=nome, cpf=next(_CPFS), email="j@x.org", telefone="47999990000")
    sessao.add(padrinho)
    await sessao.commit()
    return padrinho


async def _pet(
    sessao: AsyncSession,
    nome: str = "Rex",
    situacao: SituacaoAdocaoPet = SituacaoAdocaoPet.DISPONIVEL,
    saude: StatusSaudePet = StatusSaudePet.SAUDAVEL,
) -> Pet:
    pet = Pet(
        nome=nome,
        especie=EspeciePet.CACHORRO,
        idade=2,
        data_resgate=date(2025, 1, 1),
        situacao_adocao=situacao,
        status_saude=saude,
        doenca_atual="Cinomose" if saude == StatusSaudePet.EM_TRATAMENTO_MEDICO else None,
    )
    sessao.add(pet)
    await sessao.commit()
    return pet


async def _apadrinhar(
    client: AsyncClient, cabecalho: dict, padrinho_id: int, pet_id: int, **campos
) -> dict:
    corpo = {
        "padrinho_id": padrinho_id,
        "pet_id": pet_id,
        "valor_mensal": "50.00",
        "data_inicio": (HOJE - timedelta(days=30)).isoformat(),
        **campos,
    }
    resposta = await client.post("/apadrinhamentos", json=corpo, headers=cabecalho)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def _processo_aprovado(sessao: AsyncSession, pet: Pet) -> ProcessoAdocao:
    adotante = Adotante(
        nome="Ana", cpf=next(_CPFS), email="a@x.org", telefone="1", endereco="Rua 1"
    )
    sessao.add(adotante)
    await sessao.commit()
    pet.situacao_adocao = SituacaoAdocaoPet.EM_PROCESSO_ADOCAO
    processo = ProcessoAdocao(
        pet_id=pet.id, adotante_id=adotante.id, status=StatusProcessoAdocao.APROVADO
    )
    sessao.add(processo)
    await sessao.commit()
    return processo


def _finalizar(processo_id: int):
    return ProcessoAdocaoAtualizarStatus(status=StatusProcessoAdocao.FINALIZADO)


# ------------------------------------------------------------------ H7.1-4


async def test_cria_apadrinhamento_ativo_com_nomes(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    padrinho = await _padrinho(sessao)
    pet = await _pet(sessao)

    corpo = await _apadrinhar(client, cabecalho_voluntario, padrinho.id, pet.id)

    assert corpo["padrinho_nome"] == "Joana"
    assert corpo["pet_nome"] == "Rex"
    assert Decimal(corpo["valor_mensal"]) == Decimal("50.00")
    assert corpo["ativo"] is True
    assert corpo["data_fim"] is None


@pytest.mark.parametrize(
    ("campos", "status"),
    [
        ({"valor_mensal": "0"}, 422),
        ({"valor_mensal": "10.123"}, 422),
        ({"data_inicio": (HOJE + timedelta(days=1)).isoformat()}, 422),
        ({"padrinho_id": 999}, 404),
        ({"pet_id": 999}, 404),
    ],
)
async def test_dados_invalidos(
    client: AsyncClient,
    sessao: AsyncSession,
    cabecalho_voluntario: dict,
    campos: dict,
    status: int,
) -> None:
    padrinho = await _padrinho(sessao)
    pet = await _pet(sessao)
    corpo = {
        "padrinho_id": padrinho.id,
        "pet_id": pet.id,
        "valor_mensal": "50.00",
        "data_inicio": HOJE.isoformat(),
        **campos,
    }

    resposta = await client.post("/apadrinhamentos", json=corpo, headers=cabecalho_voluntario)

    assert resposta.status_code == status, resposta.text


async def test_um_ativo_por_padrinho_e_pet_e_reapadrinhar_depois_de_encerrar(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    """A-08: a versao recebida nao deixava apadrinhar de novo o mesmo pet, nunca."""
    padrinho = await _padrinho(sessao)
    pet = await _pet(sessao)
    primeiro = await _apadrinhar(client, cabecalho_voluntario, padrinho.id, pet.id)

    repetido = await client.post(
        "/apadrinhamentos",
        json={
            "padrinho_id": padrinho.id,
            "pet_id": pet.id,
            "valor_mensal": "80.00",
            "data_inicio": HOJE.isoformat(),
        },
        headers=cabecalho_voluntario,
    )
    await client.post(
        f"/apadrinhamentos/{primeiro['id']}/encerramento",
        json={"data_fim": HOJE.isoformat()},
        headers=cabecalho_voluntario,
    )
    de_novo = await _apadrinhar(
        client, cabecalho_voluntario, padrinho.id, pet.id, valor_mensal="80.00"
    )

    assert repetido.status_code == 409
    assert de_novo["ativo"] is True


async def test_pet_pode_ter_varios_padrinhos(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _pet(sessao)
    for nome in ("Joana", "Paulo"):
        await _apadrinhar(client, cabecalho_voluntario, (await _padrinho(sessao, nome)).id, pet.id)

    contagem = await client.get(f"/pets/{pet.id}/padrinhos", headers=cabecalho_voluntario)

    assert contagem.json() == {"pet_id": pet.id, "ativos": 2}


async def test_dois_cadastros_iguais_ao_mesmo_tempo_o_segundo_recebe_409(
    sessao: AsyncSession,
) -> None:
    """O segundo espera a trava do pet (a insercao do primeiro prende a linha pela chave
    estrangeira) e, ao entrar, ja enxerga o primeiro: 409 pela checagem previa. O indice
    parcial fica como rede de seguranca -- coberto no teste seguinte."""
    padrinho = await _padrinho(sessao)
    pet = await _pet(sessao)
    dados = ApadrinhamentoCriar(
        padrinho_id=padrinho.id, pet_id=pet.id, valor_mensal=Decimal("50"), data_inicio=HOJE
    )

    async def _cadastrar() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_apadrinhamento.criar(sessao_local, dados, hoje=HOJE)

    async with FabricaSessaoTeste() as primeira:
        primeira.add(
            Apadrinhamento(
                padrinho_id=padrinho.id, pet_id=pet.id, valor_mensal=50, data_inicio=HOJE
            )
        )
        await primeira.flush()  # o segundo esbarra no indice e espera
        tarefa = asyncio.create_task(_cadastrar())
        await esperar_conexoes_bloqueadas(1)
        await primeira.commit()

    with pytest.raises(ConflitoError):
        await tarefa


async def test_banco_recusa_segundo_ativo_do_mesmo_padrinho_e_pet(sessao: AsyncSession) -> None:
    """A rede de seguranca no banco, para quem gravar sem passar pelo servico."""
    padrinho = await _padrinho(sessao)
    pet = await _pet(sessao)
    for _ in range(2):
        sessao.add(
            Apadrinhamento(
                padrinho_id=padrinho.id, pet_id=pet.id, valor_mensal=50, data_inicio=HOJE
            )
        )
    with pytest.raises(IntegrityError):
        await sessao.commit()
    await sessao.rollback()


async def test_pet_adotado_nao_recebe_apadrinhamento(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    padrinho = await _padrinho(sessao)
    pet = await _pet(sessao, situacao=SituacaoAdocaoPet.ADOTADO)

    resposta = await client.post(
        "/apadrinhamentos",
        json={
            "padrinho_id": padrinho.id,
            "pet_id": pet.id,
            "valor_mensal": "50",
            "data_inicio": HOJE.isoformat(),
        },
        headers=cabecalho_voluntario,
    )

    assert resposta.status_code == 422


# ------------------------------------------------------------------- H7.5 D12


async def test_finalizar_adocao_encerra_os_apadrinhamentos_ativos_do_pet(
    sessao: AsyncSession,
) -> None:
    pet = await _pet(sessao)
    outro_pet = await _pet(sessao, "Mingau")
    joana, paulo = await _padrinho(sessao, "Joana"), await _padrinho(sessao, "Paulo")
    antigo = Apadrinhamento(
        padrinho_id=joana.id,
        pet_id=pet.id,
        valor_mensal=30,
        data_inicio=HOJE - timedelta(days=200),
        data_fim=HOJE - timedelta(days=100),
    )
    ativos = [
        Apadrinhamento(padrinho_id=p.id, pet_id=pet.id, valor_mensal=50, data_inicio=HOJE)
        for p in (joana, paulo)
    ]
    do_outro_pet = Apadrinhamento(
        padrinho_id=joana.id, pet_id=outro_pet.id, valor_mensal=50, data_inicio=HOJE
    )
    sessao.add_all([antigo, *ativos, do_outro_pet])
    await sessao.commit()
    processo = await _processo_aprovado(sessao, pet)

    await servico_processo.atualizar_status_processo(
        sessao, processo.id, _finalizar(processo.id), hoje=HOJE
    )

    for registro in (antigo, *ativos, do_outro_pet):
        await sessao.refresh(registro)
    assert [a.data_fim for a in ativos] == [HOJE, HOJE]
    assert antigo.data_fim == HOJE - timedelta(days=100)  # o encerrado nao muda
    assert do_outro_pet.data_fim is None  # o de outro pet nao muda


async def test_finalizacao_recusada_nao_encerra_nada(sessao: AsyncSession) -> None:
    """Pet em tratamento nao finaliza (D1). O encerramento vem junto: nada muda."""
    pet = await _pet(sessao, saude=StatusSaudePet.EM_TRATAMENTO_MEDICO)
    ativo = Apadrinhamento(
        padrinho_id=(await _padrinho(sessao)).id, pet_id=pet.id, valor_mensal=50, data_inicio=HOJE
    )
    sessao.add(ativo)
    await sessao.commit()
    processo = await _processo_aprovado(sessao, pet)

    with pytest.raises(RegraNegocioError):
        await servico_processo.atualizar_status_processo(
            sessao, processo.id, _finalizar(processo.id), hoje=HOJE
        )

    await sessao.rollback()
    await sessao.refresh(ativo)
    assert ativo.data_fim is None


async def test_cancelar_a_adocao_nao_encerra(sessao: AsyncSession) -> None:
    pet = await _pet(sessao)
    ativo = Apadrinhamento(
        padrinho_id=(await _padrinho(sessao)).id, pet_id=pet.id, valor_mensal=50, data_inicio=HOJE
    )
    sessao.add(ativo)
    await sessao.commit()
    processo = await _processo_aprovado(sessao, pet)

    await servico_processo.atualizar_status_processo(
        sessao,
        processo.id,
        ProcessoAdocaoAtualizarStatus(status=StatusProcessoAdocao.CANCELADO),
        hoje=HOJE,
    )

    await sessao.refresh(ativo)
    assert ativo.data_fim is None


async def test_apadrinhamento_criado_durante_a_finalizacao_nao_fica_ativo(
    sessao: AsyncSession,
) -> None:
    """A finalizacao trava o pet; o apadrinhamento que chega espera e ve o pet adotado.
    Sem a trava, ele entraria depois do encerramento e ficaria ativo num pet adotado."""
    pet = await _pet(sessao)
    padrinho = await _padrinho(sessao)
    processo = await _processo_aprovado(sessao, pet)
    dados = ApadrinhamentoCriar(
        padrinho_id=padrinho.id, pet_id=pet.id, valor_mensal=Decimal("50"), data_inicio=HOJE
    )

    async def _apadrinhar_agora() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_apadrinhamento.criar(sessao_local, dados, hoje=HOJE)

    async with FabricaSessaoTeste() as quem_finaliza:
        travado = await quem_finaliza.get(Pet, pet.id, with_for_update=True)
        tarefa = asyncio.create_task(_apadrinhar_agora())
        await esperar_conexoes_bloqueadas(1)
        travado.situacao_adocao = SituacaoAdocaoPet.ADOTADO
        await quem_finaliza.execute(
            ProcessoAdocao.__table__.update()
            .where(ProcessoAdocao.id == processo.id)
            .values(status=StatusProcessoAdocao.FINALIZADO)
        )
        await quem_finaliza.commit()

    with pytest.raises(RegraNegocioError):
        await tarefa
    assert (await sessao.scalars(select(Apadrinhamento))).all() == []


async def test_finalizacao_que_chega_durante_o_apadrinhamento_encerra_o_novo(
    sessao: AsyncSession,
) -> None:
    """A outra ordem: o apadrinhamento trava o pet primeiro; a finalizacao espera e, ao
    entrar, ja enxerga o apadrinhamento novo e o encerra."""
    pet = await _pet(sessao)
    padrinho = await _padrinho(sessao)
    processo = await _processo_aprovado(sessao, pet)

    async def _finalizar_agora() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_processo.atualizar_status_processo(
                sessao_local, processo.id, _finalizar(processo.id), hoje=HOJE
            )

    async with FabricaSessaoTeste() as quem_apadrinha:
        await quem_apadrinha.get(Pet, pet.id, with_for_update=True)
        quem_apadrinha.add(
            Apadrinhamento(
                padrinho_id=padrinho.id, pet_id=pet.id, valor_mensal=50, data_inicio=HOJE
            )
        )
        tarefa = asyncio.create_task(_finalizar_agora())
        await esperar_conexoes_bloqueadas(1)
        await quem_apadrinha.commit()
    await tarefa

    [apadrinhamento] = (await sessao.scalars(select(Apadrinhamento))).all()
    await sessao.refresh(apadrinhamento)
    assert apadrinhamento.data_fim == HOJE


# --------------------------------------------------------------------- H7.3


async def test_encerrar(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    padrinho = await _padrinho(sessao)
    pet = await _pet(sessao)
    criado = await _apadrinhar(
        client,
        cabecalho_voluntario,
        padrinho.id,
        pet.id,
        data_inicio=(HOJE - timedelta(days=10)).isoformat(),
    )
    url = f"/apadrinhamentos/{criado['id']}/encerramento"

    futuro = await client.post(
        url, json={"data_fim": (HOJE + timedelta(days=1)).isoformat()}, headers=cabecalho_voluntario
    )
    antes_do_inicio = await client.post(
        url,
        json={"data_fim": (HOJE - timedelta(days=11)).isoformat()},
        headers=cabecalho_voluntario,
    )
    certo = await client.post(
        url, json={"data_fim": HOJE.isoformat()}, headers=cabecalho_voluntario
    )
    de_novo = await client.post(
        url, json={"data_fim": HOJE.isoformat()}, headers=cabecalho_voluntario
    )
    inexistente = await client.post(
        "/apadrinhamentos/999/encerramento",
        json={"data_fim": HOJE.isoformat()},
        headers=cabecalho_voluntario,
    )

    assert futuro.status_code == 422
    assert antes_do_inicio.status_code == 422
    assert certo.status_code == 200
    assert certo.json()["ativo"] is False
    assert de_novo.status_code == 422
    assert inexistente.status_code == 404


# --------------------------------------------------------------------- H7.6


async def test_listagem_com_filtros_e_ativos_primeiro(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    joana, paulo = await _padrinho(sessao, "Joana"), await _padrinho(sessao, "Paulo")
    rex, mingau = await _pet(sessao, "Rex"), await _pet(sessao, "Mingau")
    encerrado = await _apadrinhar(client, cabecalho_voluntario, joana.id, rex.id)
    await client.post(
        f"/apadrinhamentos/{encerrado['id']}/encerramento",
        json={"data_fim": HOJE.isoformat()},
        headers=cabecalho_voluntario,
    )
    ativo = await _apadrinhar(client, cabecalho_voluntario, joana.id, mingau.id)
    await _apadrinhar(client, cabecalho_voluntario, paulo.id, rex.id)

    da_joana = await client.get(
        f"/apadrinhamentos?padrinho_id={joana.id}&incluir_encerrados=true",
        headers=cabecalho_voluntario,
    )
    so_ativos_da_joana = await client.get(
        f"/apadrinhamentos?padrinho_id={joana.id}", headers=cabecalho_voluntario
    )
    do_rex = await client.get(f"/apadrinhamentos?pet_id={rex.id}", headers=cabecalho_voluntario)

    assert [item["id"] for item in da_joana.json()["itens"]] == [ativo["id"], encerrado["id"]]
    assert so_ativos_da_joana.json()["total"] == 1
    assert [item["padrinho_nome"] for item in do_rex.json()["itens"]] == ["Paulo"]


async def test_veterinario_ve_so_a_contagem(
    client: AsyncClient,
    sessao: AsyncSession,
    cabecalho_voluntario: dict,
    cabecalho_veterinario: dict,
) -> None:
    pet = await _pet(sessao)
    await _apadrinhar(client, cabecalho_voluntario, (await _padrinho(sessao)).id, pet.id)

    contagem = await client.get(f"/pets/{pet.id}/padrinhos", headers=cabecalho_veterinario)
    lista = await client.get(f"/apadrinhamentos?pet_id={pet.id}", headers=cabecalho_veterinario)
    sem_pet = await client.get("/pets/999/padrinhos", headers=cabecalho_veterinario)

    assert contagem.json() == {"pet_id": pet.id, "ativos": 1}
    assert lista.status_code == 403
    assert sem_pet.status_code == 404


# ------------------------------------------------------------------ historico


async def test_banco_recusa_apagar_pet_ou_padrinho_com_apadrinhamento(
    sessao: AsyncSession,
) -> None:
    """A-09: a versao recebida apagava o apadrinhamento em cascata."""
    pet = await _pet(sessao)
    padrinho = await _padrinho(sessao)
    sessao.add(
        Apadrinhamento(padrinho_id=padrinho.id, pet_id=pet.id, valor_mensal=50, data_inicio=HOJE)
    )
    await sessao.commit()

    for registro in (pet, padrinho):
        await sessao.delete(registro)
        with pytest.raises(IntegrityError):
            await sessao.commit()
        await sessao.rollback()


# ----------------------------------------------------------------------- H8


async def test_doacao_com_destino(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _pet(sessao)
    base = {"valor": "25.00", "data": HOJE.isoformat(), "tipo": "pontual", "doador_nome": "Ana"}

    com_pet = await client.post(
        "/doacoes", json={**base, "pet_id": pet.id}, headers=cabecalho_voluntario
    )
    geral = await client.post("/doacoes", json=base, headers=cabecalho_voluntario)
    pet_inexistente = await client.post(
        "/doacoes", json={**base, "pet_id": 999}, headers=cabecalho_voluntario
    )

    assert com_pet.status_code == 201
    assert com_pet.json()["pet_id"] == pet.id
    assert geral.json()["pet_id"] is None
    assert pet_inexistente.status_code == 404


async def test_encerramento_manual_durante_a_finalizacao_mantem_a_data_escolhida(
    sessao: AsyncSession,
) -> None:
    """A finalizacao so encerra quem ainda esta ativo (WHERE data_fim IS NULL). Se alguem
    encerrou o apadrinhamento no mesmo instante, a data escolhida pela pessoa vale."""
    pet = await _pet(sessao)
    ativo = Apadrinhamento(
        padrinho_id=(await _padrinho(sessao)).id,
        pet_id=pet.id,
        valor_mensal=50,
        data_inicio=HOJE - timedelta(days=60),
    )
    sessao.add(ativo)
    await sessao.commit()
    processo = await _processo_aprovado(sessao, pet)
    escolhida = HOJE - timedelta(days=5)

    async def _finalizar_agora() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_processo.atualizar_status_processo(
                sessao_local, processo.id, _finalizar(processo.id), hoje=HOJE
            )

    async with FabricaSessaoTeste() as quem_encerra:
        travado = await quem_encerra.get(Apadrinhamento, ativo.id, with_for_update=True)
        travado.data_fim = escolhida
        await quem_encerra.flush()
        tarefa = asyncio.create_task(_finalizar_agora())
        await esperar_conexoes_bloqueadas(1)
        await quem_encerra.commit()
    await tarefa

    await sessao.refresh(ativo)
    assert ativo.data_fim == escolhida
