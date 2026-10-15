"""Fase 2, H4 e H5: catalogo de vacinas e cartao de vacinacao.

Criterios em docs/HISTORIAS-FASE-2.md.
"""

import asyncio
import unicodedata
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RegraNegocioError
from app.core.tempo import hoje_na_ong
from app.esquemas.vacina import AplicacaoCriar, StatusVacina, VacinaCriar
from app.modelos.enums import EspeciePet, PerfilUsuario
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.modelos.vacina import (
    AplicacaoVacina,
    Vacina,
    chave_do_nome_vacina,
    normalizar_nome_vacina,
)
from app.servicos import vacinacao as servico_vacinacao
from testes.conftest import FabricaSessaoTeste, cabecalho_do_perfil, esperar_conexoes_bloqueadas

HOJE = hoje_na_ong()


def _dia(deslocamento: int) -> str:
    return (HOJE + timedelta(days=deslocamento)).isoformat()


async def _pet(sessao: AsyncSession, especie: EspeciePet = EspeciePet.CACHORRO) -> Pet:
    pet = Pet(nome="Rex", especie=especie, idade=3, data_resgate=date(2025, 1, 10))
    sessao.add(pet)
    await sessao.commit()
    await sessao.refresh(pet)
    return pet


async def _vacina(
    sessao: AsyncSession,
    nome: str = "V10",
    especie: EspeciePet | None = EspeciePet.CACHORRO,
    ativa: bool = True,
) -> Vacina:
    vacina = Vacina(nome=nome, especie=especie, intervalo_reforco_dias=365, ativa=ativa)
    sessao.add(vacina)
    await sessao.commit()
    await sessao.refresh(vacina)
    return vacina


async def _veterinario(sessao: AsyncSession, email: str = "vet2@x.org") -> Usuario:
    usuario = Usuario(
        nome="Dra. Paula", email=email, senha_hash="x", perfil=PerfilUsuario.VETERINARIO
    )
    sessao.add(usuario)
    await sessao.commit()
    await sessao.refresh(usuario)
    return usuario


async def _aplicar(
    client: AsyncClient, pet_id: int, vacina_id: int, cabecalho: dict, **campos
) -> dict:
    resposta = await client.post(
        f"/pets/{pet_id}/aplicacoes-vacina",
        json={"vacina_id": vacina_id, "data_aplicacao": _dia(-10), **campos},
        headers=cabecalho,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def _cartao(client: AsyncClient, pet_id: int, cabecalho: dict) -> dict:
    resposta = await client.get(f"/pets/{pet_id}/cartao-vacinacao", headers=cabecalho)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# ================================================================== H4 catalogo


@pytest.mark.parametrize("perfil", [PerfilUsuario.ADMIN, PerfilUsuario.VETERINARIO])
async def test_admin_e_veterinario_cadastram_vacina(
    client: AsyncClient, sessao: AsyncSession, perfil: PerfilUsuario
) -> None:
    resposta = await client.post(
        "/vacinas",
        json={"nome": "  Lyme  ", "especie": "cachorro", "intervalo_reforco_dias": 365},
        headers=await cabecalho_do_perfil(sessao, perfil),
    )

    assert resposta.status_code == 201
    assert resposta.json() == {
        "id": resposta.json()["id"],
        "nome": "Lyme",
        "especie": "cachorro",
        "intervalo_reforco_dias": 365,
        "ativa": True,
    }


async def test_voluntario_consulta_mas_nao_mantem_o_catalogo(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    vacina = await _vacina(sessao)

    lista = await client.get("/vacinas", headers=cabecalho_voluntario)
    criar = await client.post("/vacinas", json={"nome": "Lyme"}, headers=cabecalho_voluntario)
    editar = await client.patch(
        f"/vacinas/{vacina.id}", json={"ativa": False}, headers=cabecalho_voluntario
    )

    assert lista.status_code == 200
    assert criar.status_code == 403
    assert editar.status_code == 403


@pytest.mark.parametrize("nome", ["V10", "v10", " v10 ", "V10  "])
async def test_nome_repetido_sem_diferenciar_maiusculas_nem_espacos(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict, nome: str
) -> None:
    await _vacina(sessao, "V10")

    resposta = await client.post("/vacinas", json={"nome": nome}, headers=cabecalho_veterinario)

    assert resposta.status_code == 409


async def test_banco_tambem_recusa_nome_repetido(sessao: AsyncSession) -> None:
    """O indice unico vale mesmo para quem gravar sem passar pela API."""
    await _vacina(sessao, "V10")
    sessao.add(Vacina(nome=" v10", especie=EspeciePet.CACHORRO))

    with pytest.raises(IntegrityError):
        await sessao.commit()
    await sessao.rollback()


@pytest.mark.parametrize(
    "nome",
    [
        unicodedata.normalize("NFD", "Antirrábica"),  # acento separado da letra
        "ANTIRRÁBICA",  # maiuscula acentuada
        " antirrábica ",
    ],
)
async def test_nome_repetido_com_acento_em_outra_forma(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict, nome: str
) -> None:
    """Visualmente igual, gravado diferente: a chave (NFC + casefold) e a mesma."""
    await _vacina(sessao, "Antirrábica", None)

    resposta = await client.post("/vacinas", json={"nome": nome}, headers=cabecalho_veterinario)

    assert resposta.status_code == 409


def test_chave_do_nome_nao_depende_do_banco() -> None:
    """O lower() do Postgres so trata acento com collation como en_US.utf8; a chave e
    calculada no Python e vale igual em banco com collation C."""
    assert chave_do_nome_vacina("ANTIRRÁBICA") == chave_do_nome_vacina(" antirrábica ")
    assert chave_do_nome_vacina(unicodedata.normalize("NFD", "Giárdia")) == "giárdia"
    assert normalizar_nome_vacina(unicodedata.normalize("NFD", " Giárdia ")) == "Giárdia"


async def test_nome_gravado_em_nfc_e_chave_acompanha_a_troca_de_nome(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    criada = await client.post(
        "/vacinas",
        json={"nome": unicodedata.normalize("NFD", "Giárdia")},
        headers=cabecalho_veterinario,
    )
    assert criada.json()["nome"] == "Giárdia"  # NFC: 7 caracteres, nao 8

    await client.patch(
        f"/vacinas/{criada.json()['id']}",
        json={"nome": "Giárdia canina"},
        headers=cabecalho_veterinario,
    )
    # O nome antigo ficou livre: a chave foi junto com o nome.
    de_novo = await client.post("/vacinas", json={"nome": "giárdia"}, headers=cabecalho_veterinario)
    assert de_novo.status_code == 201


async def test_dois_cadastros_iguais_ao_mesmo_tempo_o_segundo_recebe_409(
    sessao: AsyncSession,
) -> None:
    """Os dois passam pela consulta antes de gravar; o indice barra o segundo."""

    async def _cadastrar() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_vacinacao.criar_vacina(sessao_local, VacinaCriar(nome="v10"))

    async with FabricaSessaoTeste() as primeira:
        primeira.add(Vacina(nome="V10", especie=EspeciePet.CACHORRO))
        await primeira.flush()  # grava sem commit: o segundo esbarra no indice e espera
        tarefa = asyncio.create_task(_cadastrar())
        await esperar_conexoes_bloqueadas(1)
        await primeira.commit()

    with pytest.raises(ConflitoError):
        await tarefa
    assert len((await sessao.scalars(select(Vacina))).all()) == 1


async def test_desativar_tira_das_aplicacoes_novas_mas_nao_do_cartao(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    await _aplicar(client, pet.id, vacina.id, cabecalho_veterinario, proxima_dose=_dia(5))

    desativar = await client.patch(
        f"/vacinas/{vacina.id}", json={"ativa": False}, headers=cabecalho_veterinario
    )
    ativas = await client.get("/vacinas", headers=cabecalho_veterinario)
    todas = await client.get("/vacinas?incluir_inativas=true", headers=cabecalho_veterinario)
    nova_aplicacao = await client.post(
        f"/pets/{pet.id}/aplicacoes-vacina",
        json={"vacina_id": vacina.id, "data_aplicacao": _dia(-1)},
        headers=cabecalho_veterinario,
    )
    cartao = await _cartao(client, pet.id, cabecalho_veterinario)

    assert desativar.json()["ativa"] is False
    assert ativas.json() == []
    assert [item["nome"] for item in todas.json()] == ["V10"]
    assert nova_aplicacao.status_code == 422
    assert cartao["situacao"][0]["vacina_nome"] == "V10"
    assert cartao["situacao"][0]["vacina_ativa"] is False
    assert cartao["situacao"][0]["status"] == "vencendo"


async def test_editar_vacina(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    vacina = await _vacina(sessao, "V10")
    await _vacina(sessao, "V8")
    url = f"/vacinas/{vacina.id}"

    mesmo_nome = await client.patch(url, json={"nome": "v10"}, headers=cabecalho_veterinario)
    nome_de_outra = await client.patch(url, json={"nome": " V8 "}, headers=cabecalho_veterinario)
    nome_nulo = await client.patch(url, json={"nome": None}, headers=cabecalho_veterinario)
    ativa_nula = await client.patch(url, json={"ativa": None}, headers=cabecalho_veterinario)
    sem_intervalo = await client.patch(
        url, json={"intervalo_reforco_dias": None}, headers=cabecalho_veterinario
    )
    especie = await client.patch(url, json={"especie": "gato"}, headers=cabecalho_veterinario)
    inexistente = await client.patch(
        "/vacinas/999", json={"ativa": False}, headers=cabecalho_veterinario
    )

    assert mesmo_nome.status_code == 200  # a propria vacina nao conta como repetida
    assert mesmo_nome.json()["nome"] == "v10"
    assert nome_de_outra.status_code == 409
    assert nome_nulo.status_code == 422
    assert ativa_nula.status_code == 422
    assert sem_intervalo.json()["intervalo_reforco_dias"] is None
    assert especie.json()["especie"] == "cachorro"  # especie nao muda
    assert inexistente.status_code == 404


def test_contrato_do_patch_so_aceita_nulo_no_intervalo() -> None:
    from app.main import app

    esquema = app.openapi()["components"]["schemas"]["VacinaAtualizar"]["properties"]

    assert "anyOf" not in esquema["nome"]
    assert "anyOf" not in esquema["ativa"]
    assert {"type": "null"} in esquema["intervalo_reforco_dias"]["anyOf"]


# ================================================================ H5 aplicacao


async def test_veterinario_registra_aplicacao_assinada_por_ele(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    outro = await _veterinario(sessao)

    corpo = await _aplicar(
        client,
        pet.id,
        vacina.id,
        cabecalho_veterinario,
        proxima_dose=_dia(355),
        lote="  AB123 ",
        observacao="   ",
        veterinario_id=outro.id,
    )

    assert corpo["veterinario_id"] != outro.id
    assert corpo["vacina_nome"] == "V10"
    assert corpo["lote"] == "AB123"
    assert corpo["observacao"] is None


async def test_datas_da_aplicacao(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    url = f"/pets/{pet.id}/aplicacoes-vacina"

    futura = await client.post(
        url, json={"vacina_id": vacina.id, "data_aplicacao": _dia(1)}, headers=cabecalho_veterinario
    )
    proxima_igual = await client.post(
        url,
        json={"vacina_id": vacina.id, "data_aplicacao": _dia(-5), "proxima_dose": _dia(-5)},
        headers=cabecalho_veterinario,
    )
    # Cartao antigo: reforco ja vencido, mas depois da aplicacao. Vale.
    cartao_antigo = await client.post(
        url,
        json={"vacina_id": vacina.id, "data_aplicacao": _dia(-400), "proxima_dose": _dia(-35)},
        headers=cabecalho_veterinario,
    )

    assert futura.status_code == 422
    assert proxima_igual.status_code == 422
    assert cartao_antigo.status_code == 201


async def test_hoje_e_o_dia_de_brasilia(sessao: AsyncSession) -> None:
    """22h de 15/10 em Brasilia ja e 16/10 em UTC."""
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    veterinario = await _veterinario(sessao)
    hoje = hoje_na_ong(datetime(2026, 10, 16, 1, 0, tzinfo=UTC))

    aceita = await servico_vacinacao.registrar_aplicacao(
        sessao,
        pet.id,
        AplicacaoCriar(vacina_id=vacina.id, data_aplicacao=date(2026, 10, 15)),
        veterinario,
        hoje=hoje,
    )
    assert aceita.data_aplicacao == date(2026, 10, 15)
    with pytest.raises(RegraNegocioError):
        await servico_vacinacao.registrar_aplicacao(
            sessao,
            pet.id,
            AplicacaoCriar(vacina_id=vacina.id, data_aplicacao=date(2026, 10, 16)),
            veterinario,
            hoje=hoje,
        )


async def test_vacina_precisa_ser_da_especie_do_pet(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    gato = await _pet(sessao, EspeciePet.GATO)
    coelho = await _pet(sessao, EspeciePet.OUTRO)
    v10 = await _vacina(sessao, "V10", EspeciePet.CACHORRO)
    antirrabica = await _vacina(sessao, "Antirrabica", None)

    v10_no_gato = await client.post(
        f"/pets/{gato.id}/aplicacoes-vacina",
        json={"vacina_id": v10.id, "data_aplicacao": _dia(-1)},
        headers=cabecalho_veterinario,
    )

    assert v10_no_gato.status_code == 422
    await _aplicar(client, gato.id, antirrabica.id, cabecalho_veterinario)
    await _aplicar(client, coelho.id, antirrabica.id, cabecalho_veterinario)


async def test_pet_ou_vacina_inexistente_responde_404(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)

    sem_pet = await client.post(
        "/pets/999/aplicacoes-vacina",
        json={"vacina_id": vacina.id, "data_aplicacao": _dia(-1)},
        headers=cabecalho_veterinario,
    )
    sem_vacina = await client.post(
        f"/pets/{pet.id}/aplicacoes-vacina",
        json={"vacina_id": 999, "data_aplicacao": _dia(-1)},
        headers=cabecalho_veterinario,
    )
    cartao = await client.get("/pets/999/cartao-vacinacao", headers=cabecalho_veterinario)

    assert sem_pet.status_code == 404
    assert sem_vacina.status_code == 404
    assert cartao.status_code == 404


async def test_mesma_vacina_no_mesmo_dia_so_uma_valida(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    primeira = await _aplicar(client, pet.id, vacina.id, cabecalho_veterinario)

    repetida = await client.post(
        f"/pets/{pet.id}/aplicacoes-vacina",
        json={"vacina_id": vacina.id, "data_aplicacao": _dia(-10)},
        headers=cabecalho_veterinario,
    )
    await client.post(
        f"/aplicacoes-vacina/{primeira['id']}/anulacao",
        json={"motivo": "Lote errado"},
        headers=cabecalho_veterinario,
    )

    assert repetida.status_code == 409
    # Anulada, ela sai da regra: registrar de novo no mesmo dia volta a valer.
    await _aplicar(client, pet.id, vacina.id, cabecalho_veterinario)


async def test_duas_aplicacoes_iguais_ao_mesmo_tempo_a_segunda_recebe_409(
    sessao: AsyncSession,
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    veterinario = await _veterinario(sessao)
    dados = AplicacaoCriar(vacina_id=vacina.id, data_aplicacao=HOJE - timedelta(days=1))

    async def _registrar() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_vacinacao.registrar_aplicacao(
                sessao_local, pet.id, dados, veterinario, hoje=HOJE
            )

    async with FabricaSessaoTeste() as primeira:
        primeira.add(
            AplicacaoVacina(
                pet_id=pet.id,
                vacina_id=vacina.id,
                veterinario_id=veterinario.id,
                data_aplicacao=dados.data_aplicacao,
            )
        )
        await primeira.flush()
        tarefa = asyncio.create_task(_registrar())
        await esperar_conexoes_bloqueadas(1)
        await primeira.commit()

    with pytest.raises(ConflitoError):
        await tarefa


async def test_aplicacao_e_desativacao_ao_mesmo_tempo(sessao: AsyncSession) -> None:
    """A desativacao trava a vacina; a aplicacao que chega espera e ve a vacina inativa."""
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    veterinario = await _veterinario(sessao)

    async def _registrar() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_vacinacao.registrar_aplicacao(
                sessao_local,
                pet.id,
                AplicacaoCriar(vacina_id=vacina.id, data_aplicacao=HOJE),
                veterinario,
                hoje=HOJE,
            )

    async with FabricaSessaoTeste() as quem_desativa:
        travada = await quem_desativa.get(Vacina, vacina.id, with_for_update=True)
        tarefa = asyncio.create_task(_registrar())
        await esperar_conexoes_bloqueadas(1)
        travada.ativa = False
        await quem_desativa.commit()

    with pytest.raises(RegraNegocioError):
        await tarefa
    assert (await sessao.scalars(select(AplicacaoVacina))).all() == []


@pytest.mark.parametrize("perfil", [PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO])
async def test_equipe_consulta_o_cartao_mas_nao_aplica_nem_anula(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict, perfil: PerfilUsuario
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    aplicacao = await _aplicar(client, pet.id, vacina.id, cabecalho_veterinario)
    cabecalho = await cabecalho_do_perfil(sessao, perfil)

    cartao = await client.get(f"/pets/{pet.id}/cartao-vacinacao", headers=cabecalho)
    aplicar = await client.post(
        f"/pets/{pet.id}/aplicacoes-vacina",
        json={"vacina_id": vacina.id, "data_aplicacao": _dia(-2)},
        headers=cabecalho,
    )
    anular = await client.post(
        f"/aplicacoes-vacina/{aplicacao['id']}/anulacao", json={"motivo": "x"}, headers=cabecalho
    )

    assert cartao.status_code == 200
    assert aplicar.status_code == 403
    assert anular.status_code == 403


# ================================================================== H5 cartao


@pytest.mark.parametrize(
    ("proxima_dose", "status"),
    [
        (None, StatusVacina.SEM_REFORCO),
        (-1, StatusVacina.VENCIDA),
        (0, StatusVacina.VENCENDO),  # vence hoje
        (30, StatusVacina.VENCENDO),
        (31, StatusVacina.EM_DIA),
    ],
)
def test_status_pela_proxima_dose(proxima_dose: int | None, status: StatusVacina) -> None:
    hoje = date(2026, 10, 15)
    dose = None if proxima_dose is None else hoje + timedelta(days=proxima_dose)
    assert servico_vacinacao.status_da_dose(dose, hoje) == status


async def test_cartao_vale_pela_ultima_aplicacao_mesmo_registrada_fora_de_ordem(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    """A-10: a dose antiga com reforco vencido nao deixa a vacina vencida."""
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    # Registradas fora de ordem: a mais recente primeiro.
    await _aplicar(
        client,
        pet.id,
        vacina.id,
        cabecalho_veterinario,
        data_aplicacao=_dia(-10),
        proxima_dose=_dia(355),
    )
    await _aplicar(
        client,
        pet.id,
        vacina.id,
        cabecalho_veterinario,
        data_aplicacao=_dia(-740),
        proxima_dose=_dia(-375),
    )
    await _aplicar(
        client,
        pet.id,
        vacina.id,
        cabecalho_veterinario,
        data_aplicacao=_dia(-375),
        proxima_dose=_dia(-10),
    )

    cartao = await _cartao(client, pet.id, cabecalho_veterinario)

    assert cartao["hoje"] == HOJE.isoformat()
    assert cartao["situacao"] == [
        {
            "vacina_id": vacina.id,
            "vacina_nome": "V10",
            "vacina_ativa": True,
            "ultima_aplicacao": _dia(-10),
            "proxima_dose": _dia(355),
            "status": "em_dia",
            "dias_para_vencer": 355,
        }
    ]
    assert [item["data_aplicacao"] for item in cartao["historico"]] == [
        _dia(-10),
        _dia(-375),
        _dia(-740),
    ]


async def test_anular_a_ultima_volta_para_a_anterior_e_sem_nenhuma_sai_do_cartao(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    antiga = await _aplicar(
        client,
        pet.id,
        vacina.id,
        cabecalho_veterinario,
        data_aplicacao=_dia(-400),
        proxima_dose=_dia(-35),
    )
    recente = await _aplicar(
        client,
        pet.id,
        vacina.id,
        cabecalho_veterinario,
        data_aplicacao=_dia(-35),
        proxima_dose=_dia(330),
    )

    await client.post(
        f"/aplicacoes-vacina/{recente['id']}/anulacao",
        json={"motivo": "Pet errado"},
        headers=cabecalho_veterinario,
    )
    depois_da_primeira = await _cartao(client, pet.id, cabecalho_veterinario)
    await client.post(
        f"/aplicacoes-vacina/{antiga['id']}/anulacao",
        json={"motivo": "Duplicada"},
        headers=cabecalho_veterinario,
    )
    depois_da_segunda = await _cartao(client, pet.id, cabecalho_veterinario)

    assert depois_da_primeira["situacao"][0]["status"] == "vencida"
    assert depois_da_primeira["situacao"][0]["dias_para_vencer"] == -35
    assert depois_da_segunda["situacao"] == []
    # O historico guarda as duas, marcadas como anuladas.
    historico = depois_da_segunda["historico"]
    assert [item["motivo_anulacao"] for item in historico] == ["Pet errado", "Duplicada"]
    assert all(item["anulado_por_nome"] for item in historico)


async def test_cartao_mostra_a_mais_urgente_primeiro(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    em_dia = await _vacina(sessao, "Em dia")
    sem_reforco = await _vacina(sessao, "Sem reforco")
    vencendo = await _vacina(sessao, "Vencendo")
    vencida = await _vacina(sessao, "Vencida")
    for vacina, proxima in (
        (em_dia, _dia(200)),
        (sem_reforco, None),
        (vencendo, _dia(10)),
        (vencida, _dia(-3)),
    ):
        await _aplicar(client, pet.id, vacina.id, cabecalho_veterinario, proxima_dose=proxima)

    cartao = await _cartao(client, pet.id, cabecalho_veterinario)

    assert [item["status"] for item in cartao["situacao"]] == [
        "vencida",
        "vencendo",
        "em_dia",
        "sem_reforco",
    ]


async def test_anular_aplicacao(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    aplicacao = await _aplicar(client, pet.id, vacina.id, cabecalho_veterinario)
    url = f"/aplicacoes-vacina/{aplicacao['id']}/anulacao"

    sem_motivo = await client.post(url, json={"motivo": "  "}, headers=cabecalho_veterinario)
    primeira = await client.post(url, json={"motivo": "Erro"}, headers=cabecalho_veterinario)
    segunda = await client.post(url, json={"motivo": "Erro"}, headers=cabecalho_veterinario)
    inexistente = await client.post(
        "/aplicacoes-vacina/999/anulacao", json={"motivo": "Erro"}, headers=cabecalho_veterinario
    )

    assert sem_motivo.status_code == 422
    assert primeira.status_code == 200
    assert primeira.json()["motivo_anulacao"] == "Erro"
    assert segunda.status_code == 422
    assert inexistente.status_code == 404


async def test_duas_anulacoes_ao_mesmo_tempo_so_uma_passa(sessao: AsyncSession) -> None:
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    paula = await _veterinario(sessao, "paula@x.org")
    rui = await _veterinario(sessao, "rui@x.org")
    aplicacao = AplicacaoVacina(
        pet_id=pet.id, vacina_id=vacina.id, veterinario_id=paula.id, data_aplicacao=HOJE
    )
    sessao.add(aplicacao)
    await sessao.commit()

    async def _rui_anula() -> None:
        from app.esquemas.vacina import AplicacaoAnular

        async with FabricaSessaoTeste() as sessao_local:
            await servico_vacinacao.anular_aplicacao(
                sessao_local, aplicacao.id, AplicacaoAnular(motivo="Duplicada"), rui
            )

    async with FabricaSessaoTeste() as sessao_paula:
        travada = await sessao_paula.get(AplicacaoVacina, aplicacao.id, with_for_update=True)
        tarefa = asyncio.create_task(_rui_anula())
        await esperar_conexoes_bloqueadas(1)
        travada.anulado_em = datetime.now(UTC)
        travada.anulado_por_id = paula.id
        travada.motivo_anulacao = "Pet errado"
        await sessao_paula.commit()

    with pytest.raises(RegraNegocioError):
        await tarefa
    await sessao.refresh(aplicacao)
    assert aplicacao.motivo_anulacao == "Pet errado"


# =============================================================== historico


async def test_banco_recusa_apagar_pet_ou_vacina_com_aplicacao(sessao: AsyncSession) -> None:
    """A-09: nem o pet nem a vacina levam o cartao junto."""
    pet = await _pet(sessao)
    vacina = await _vacina(sessao)
    veterinario = await _veterinario(sessao)
    sessao.add(
        AplicacaoVacina(
            pet_id=pet.id, vacina_id=vacina.id, veterinario_id=veterinario.id, data_aplicacao=HOJE
        )
    )
    await sessao.commit()

    for registro in (pet, vacina):
        await sessao.delete(registro)
        with pytest.raises(IntegrityError):
            await sessao.commit()
        await sessao.rollback()
