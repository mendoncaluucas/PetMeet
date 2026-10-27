"""Fase 3, H9: gastos e estornos de gasto e de doacao (criterios em docs/HISTORIAS-FASE-3.md)."""

import asyncio
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RegraNegocioError
from app.core.tempo import hoje_na_ong, intervalo_do_mes
from app.esquemas.gasto import EstornoCriar
from app.modelos.doacao import Doacao
from app.modelos.enums import (
    CategoriaGasto,
    EspeciePet,
    FrequenciaContribuicao,
    PerfilUsuario,
)
from app.modelos.gasto import Gasto
from app.modelos.log_auditoria import LogAuditoria
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.repositorios import painel as repo_painel
from app.servicos import doacao as servico_doacao
from app.servicos import gasto as servico_gasto
from testes.conftest import FabricaSessaoTeste, esperar_conexoes_bloqueadas

HOJE = hoje_na_ong()
SETEMBRO = date(2026, 9, 20)
OUTUBRO = date(2026, 10, 15)


def _gasto(**campos) -> dict:
    return {
        "valor": "120.50",
        "data": HOJE.isoformat(),
        "categoria": "alimentacao",
        "descricao": "Racao 15 kg",
        **campos,
    }


async def _pet(sessao: AsyncSession) -> Pet:
    pet = Pet(nome="Rex", especie=EspeciePet.CACHORRO, idade=2, data_resgate=date(2025, 1, 1))
    sessao.add(pet)
    await sessao.commit()
    return pet


async def _admin(sessao: AsyncSession) -> Usuario:
    return await sessao.scalar(select(Usuario).where(Usuario.perfil == PerfilUsuario.ADMIN))


async def _usuario(sessao: AsyncSession) -> Usuario:
    """Quem registra: o usuario que o teste ja tiver criado, ou um novo."""
    usuario = await sessao.scalar(select(Usuario).limit(1))
    if usuario is None:
        usuario = Usuario(
            nome="Equipe", email="equipe@x.org", senha_hash="x", perfil=PerfilUsuario.ADMIN
        )
        sessao.add(usuario)
        await sessao.commit()
    return usuario


async def _gasto_no_banco(
    sessao: AsyncSession, data: date = SETEMBRO, valor: str = "100.00"
) -> Gasto:
    usuario = await _usuario(sessao)
    gasto = Gasto(
        valor=Decimal(valor),
        data=data,
        categoria=CategoriaGasto.VETERINARIO_MEDICAMENTOS,
        descricao="Consulta",
        registrado_por_id=usuario.id,
    )
    sessao.add(gasto)
    await sessao.commit()
    return gasto


# ------------------------------------------------------------------ H9.1-2


async def test_equipe_registra_gasto(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _pet(sessao)

    resposta = await client.post(
        "/gastos", json=_gasto(pet_id=pet.id, descricao="  Racao  "), headers=cabecalho_voluntario
    )

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert Decimal(corpo["valor"]) == Decimal("120.50")
    assert corpo["descricao"] == "Racao"
    assert corpo["pet_nome"] == "Rex"
    assert corpo["registrado_por_nome"] == "Usuario de Teste"
    assert corpo["estorno_de_id"] is None
    assert corpo["estornado_em"] is None


@pytest.mark.parametrize(
    ("campos", "status"),
    [
        ({"data": (HOJE + timedelta(days=1)).isoformat()}, 422),
        ({"valor": "0"}, 422),
        ({"valor": "-10"}, 422),
        ({"valor": "10.123"}, 422),
        ({"descricao": "   "}, 422),
        ({"categoria": "luxo"}, 422),
        ({"pet_id": 999}, 404),
    ],
)
async def test_gasto_invalido(
    client: AsyncClient, cabecalho_voluntario: dict, campos: dict, status: int
) -> None:
    resposta = await client.post("/gastos", json=_gasto(**campos), headers=cabecalho_voluntario)
    assert resposta.status_code == status, resposta.text


def test_categorias_do_documento() -> None:
    assert {c.value for c in CategoriaGasto} == {
        "alimentacao",
        "veterinario_medicamentos",
        "vacinas",
        "higiene_limpeza",
        "estrutura_manutencao",
        "transporte",
        "outros",
    }


# ------------------------------------------------------------------- H9.3-4


async def test_admin_estorna_gasto_com_lancamento_negativo_datado_de_hoje(
    client: AsyncClient, sessao: AsyncSession, cabecalho_admin: dict
) -> None:
    pet = await _pet(sessao)
    original = (
        await client.post(
            "/gastos",
            json=_gasto(data=(HOJE - timedelta(days=40)).isoformat(), pet_id=pet.id),
            headers=cabecalho_admin,
        )
    ).json()

    resposta = await client.post(
        f"/gastos/{original['id']}/estorno",
        json={"motivo": "  Nota lancada em duplicidade "},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 201, resposta.text
    estorno = resposta.json()
    assert Decimal(estorno["valor"]) == Decimal("-120.50")
    assert estorno["data"] == HOJE.isoformat()
    assert estorno["categoria"] == original["categoria"]
    assert estorno["pet_id"] == pet.id
    assert estorno["estorno_de_id"] == original["id"]
    assert estorno["motivo_estorno"] == "Nota lancada em duplicidade"


async def test_mes_do_original_nao_muda_depois_do_estorno(sessao: AsyncSession) -> None:
    """D13: setembro foi publicado com o gasto; o estorno de outubro aparece em outubro."""
    original = await _gasto_no_banco(sessao, data=SETEMBRO, valor="100.00")
    usuario = await _usuario(sessao)

    await servico_gasto.estornar(
        sessao, original.id, EstornoCriar(motivo="Erro"), usuario, hoje=OUTUBRO
    )

    async def total_do_mes(dia: date) -> Decimal:
        inicio, fim = intervalo_do_mes(dia)
        soma = await sessao.scalar(
            select(func.coalesce(func.sum(Gasto.valor), 0)).where(
                Gasto.data >= inicio, Gasto.data < fim
            )
        )
        return Decimal(soma)

    assert await total_do_mes(SETEMBRO) == Decimal("100.00")
    assert await total_do_mes(OUTUBRO) == Decimal("-100.00")


@pytest.mark.parametrize("perfil", [PerfilUsuario.VOLUNTARIO, PerfilUsuario.VETERINARIO])
async def test_so_o_admin_estorna(
    client: AsyncClient, sessao: AsyncSession, perfil: PerfilUsuario
) -> None:
    from testes.conftest import cabecalho_do_perfil

    original = await _gasto_no_banco(sessao)
    cabecalho = await cabecalho_do_perfil(sessao, perfil)

    gasto = await client.post(
        f"/gastos/{original.id}/estorno", json={"motivo": "x"}, headers=cabecalho
    )

    assert gasto.status_code == 403


# --------------------------------------------------------------------- H9.5


async def test_estorno_nao_se_estorna_e_cada_lancamento_e_estornado_uma_vez(
    client: AsyncClient, sessao: AsyncSession, cabecalho_admin: dict
) -> None:
    original = await _gasto_no_banco(sessao)
    url = f"/gastos/{original.id}/estorno"

    estorno = await client.post(url, json={"motivo": "Erro"}, headers=cabecalho_admin)
    de_novo = await client.post(url, json={"motivo": "Erro"}, headers=cabecalho_admin)
    estorno_do_estorno = await client.post(
        f"/gastos/{estorno.json()['id']}/estorno", json={"motivo": "x"}, headers=cabecalho_admin
    )
    sem_motivo = await client.post(
        f"/gastos/{(await _gasto_no_banco(sessao)).id}/estorno",
        json={"motivo": "   "},
        headers=cabecalho_admin,
    )
    inexistente = await client.post(
        "/gastos/999/estorno", json={"motivo": "x"}, headers=cabecalho_admin
    )

    assert estorno.status_code == 201
    assert de_novo.status_code == 422
    assert de_novo.json()["detalhe"] == "Este lancamento ja foi estornado."
    assert estorno_do_estorno.status_code == 422
    assert sem_motivo.status_code == 422
    assert inexistente.status_code == 404


async def test_dois_estornos_ao_mesmo_tempo_so_um_passa(sessao: AsyncSession) -> None:
    original = await _gasto_no_banco(sessao)
    usuario = await _usuario(sessao)

    async def _estornar() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_gasto.estornar(
                sessao_local, original.id, EstornoCriar(motivo="Segundo"), usuario, hoje=HOJE
            )

    async with FabricaSessaoTeste() as primeira:
        await primeira.get(Gasto, original.id, with_for_update=True)
        primeira.add(
            Gasto(
                valor=-original.valor,
                data=HOJE,
                categoria=original.categoria,
                descricao=original.descricao,
                registrado_por_id=usuario.id,
                estorno_de_id=original.id,
                motivo_estorno="Primeiro",
            )
        )
        tarefa = asyncio.create_task(_estornar())
        await esperar_conexoes_bloqueadas(1)
        await primeira.commit()

    with pytest.raises(RegraNegocioError):
        await tarefa
    estornos = (await sessao.scalars(select(Gasto).where(Gasto.estorno_de_id.is_not(None)))).all()
    assert [e.motivo_estorno for e in estornos] == ["Primeiro"]


@pytest.mark.parametrize(
    "campos",
    [
        {"valor": Decimal("-10")},  # negativo sem ser estorno
        {"valor": Decimal("10"), "estorno_de_id": "ORIGINAL", "motivo_estorno": "x"},  # estorno +
        {"valor": Decimal("-10"), "estorno_de_id": "ORIGINAL"},  # estorno sem motivo
    ],
)
async def test_banco_recusa_lancamento_com_sinal_errado(sessao: AsyncSession, campos: dict) -> None:
    original = await _gasto_no_banco(sessao)
    if campos.get("estorno_de_id") == "ORIGINAL":
        campos = {**campos, "estorno_de_id": original.id}
    sessao.add(
        Gasto(
            data=HOJE,
            categoria=CategoriaGasto.OUTROS,
            descricao="x",
            registrado_por_id=original.registrado_por_id,
            **campos,
        )
    )
    with pytest.raises(IntegrityError):
        await sessao.commit()
    await sessao.rollback()


async def test_banco_recusa_segundo_estorno_do_mesmo_lancamento(sessao: AsyncSession) -> None:
    original = await _gasto_no_banco(sessao)
    for motivo in ("Primeiro", "Segundo"):
        sessao.add(
            Gasto(
                valor=-original.valor,
                data=HOJE,
                categoria=original.categoria,
                descricao="x",
                registrado_por_id=original.registrado_por_id,
                estorno_de_id=original.id,
                motivo_estorno=motivo,
            )
        )
    with pytest.raises(IntegrityError):
        await sessao.commit()
    await sessao.rollback()


# --------------------------------------------------------------------- H9.6


async def test_listagem_mostra_o_estorno_logo_abaixo_do_original(
    client: AsyncClient, sessao: AsyncSession, cabecalho_admin: dict
) -> None:
    antigo = await _gasto_no_banco(sessao, data=HOJE - timedelta(days=30))
    meio = await _gasto_no_banco(sessao, data=HOJE - timedelta(days=10))
    estorno = (
        await client.post(
            f"/gastos/{antigo.id}/estorno", json={"motivo": "Erro"}, headers=cabecalho_admin
        )
    ).json()

    lista = (await client.get("/gastos", headers=cabecalho_admin)).json()

    assert [item["id"] for item in lista["itens"]] == [meio.id, antigo.id, estorno["id"]]
    original = lista["itens"][1]
    assert original["estornado_em"] == HOJE.isoformat()
    assert lista["total"] == 3


async def test_filtros_da_listagem(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _pet(sessao)
    await client.post("/gastos", json=_gasto(pet_id=pet.id), headers=cabecalho_voluntario)
    await client.post("/gastos", json=_gasto(categoria="vacinas"), headers=cabecalho_voluntario)

    do_pet = await client.get(f"/gastos?pet_id={pet.id}", headers=cabecalho_voluntario)
    vacinas = await client.get("/gastos?categoria=vacinas", headers=cabecalho_voluntario)

    assert do_pet.json()["total"] == 1
    assert [item["categoria"] for item in vacinas.json()["itens"]] == ["vacinas"]


# --------------------------------------------------------------------- H9.7


async def test_registro_e_estorno_ficam_na_auditoria(
    client: AsyncClient, sessao: AsyncSession, cabecalho_admin: dict
) -> None:
    admin = await _admin(sessao)
    gasto = (await client.post("/gastos", json=_gasto(), headers=cabecalho_admin)).json()
    estorno = (
        await client.post(
            f"/gastos/{gasto['id']}/estorno", json={"motivo": "Erro"}, headers=cabecalho_admin
        )
    ).json()

    linhas = (
        await sessao.scalars(
            select(LogAuditoria).where(LogAuditoria.entidade == "gasto").order_by(LogAuditoria.id)
        )
    ).all()

    assert [(linha.acao, linha.entidade_id, linha.usuario_id) for linha in linhas] == [
        ("registro", gasto["id"], admin.id),
        ("estorno", estorno["id"], admin.id),
    ]
    assert linhas[1].dados_antigos["valor"] == "120.50"  # Decimal vira texto (A-05)
    assert linhas[1].dados_novos["valor"] == "-120.50"


# ------------------------------------------------------------------ doacoes


async def test_estorno_de_doacao_copia_origem_e_destino(
    client: AsyncClient, sessao: AsyncSession, cabecalho_admin: dict
) -> None:
    pet = await _pet(sessao)
    doacao = (
        await client.post(
            "/doacoes",
            json={
                "valor": "45.50",
                "data": (HOJE - timedelta(days=40)).isoformat(),
                "tipo": "recorrente",
                "doador_nome": "Ana",
                "pet_id": pet.id,
            },
            headers=cabecalho_admin,
        )
    ).json()

    resposta = await client.post(
        f"/doacoes/{doacao['id']}/estorno",
        json={"motivo": "Pix devolvido"},
        headers=cabecalho_admin,
    )
    lista = (await client.get("/doacoes", headers=cabecalho_admin)).json()

    assert resposta.status_code == 201, resposta.text
    estorno = resposta.json()
    assert Decimal(estorno["valor"]) == Decimal("-45.50")
    assert estorno["data"] == HOJE.isoformat()
    assert (estorno["doador_nome"], estorno["pet_id"], estorno["tipo"]) == (
        "Ana",
        pet.id,
        "recorrente",
    )
    assert doacao["registrado_por_nome"] == "Usuario de Teste"
    assert [item["id"] for item in lista["itens"]] == [doacao["id"], estorno["id"]]
    assert lista["itens"][0]["estornado_em"] == HOJE.isoformat()


async def test_painel_soma_o_estorno_no_mes_dele_e_nao_conta_como_doacao(
    sessao: AsyncSession,
) -> None:
    usuario = await _usuario(sessao)
    doacoes = [
        Doacao(
            valor=Decimal("100"),
            data=SETEMBRO,
            tipo=FrequenciaContribuicao.PONTUAL,
            doador_nome="A",
        ),
        Doacao(
            valor=Decimal("30"), data=OUTUBRO, tipo=FrequenciaContribuicao.PONTUAL, doador_nome="B"
        ),
    ]
    sessao.add_all(doacoes)
    await sessao.commit()
    await servico_doacao.estornar(
        sessao, doacoes[0].id, EstornoCriar(motivo="Erro"), usuario, hoje=OUTUBRO
    )

    setembro = await repo_painel.somar_doacoes(sessao, *intervalo_do_mes(SETEMBRO))
    outubro = await repo_painel.somar_doacoes(sessao, *intervalo_do_mes(OUTUBRO))

    assert setembro == (Decimal("100.00"), 1)
    assert outubro == (Decimal("-70.00"), 1)  # 30 - 100; o estorno nao e "mais uma doacao"


async def test_doacao_so_o_admin_estorna_e_uma_vez(
    client: AsyncClient, sessao: AsyncSession, cabecalho_admin: dict, cabecalho_voluntario: dict
) -> None:
    doacao = Doacao(
        valor=Decimal("10"), data=HOJE, tipo=FrequenciaContribuicao.PONTUAL, doador_nome="A"
    )
    sessao.add(doacao)
    await sessao.commit()
    url = f"/doacoes/{doacao.id}/estorno"

    voluntario = await client.post(url, json={"motivo": "x"}, headers=cabecalho_voluntario)
    primeira = await client.post(url, json={"motivo": "x"}, headers=cabecalho_admin)
    segunda = await client.post(url, json={"motivo": "x"}, headers=cabecalho_admin)

    assert voluntario.status_code == 403
    assert primeira.status_code == 201
    assert segunda.status_code == 422


async def test_doacao_nao_tem_data_futura(sessao: AsyncSession) -> None:
    """Doacao e recebimento. Com data futura, o portal teria dinheiro num mes que nao chegou,
    e o estorno sairia datado antes dela. "Hoje" e o dia em Brasilia: 22h de 15/10 ja e
    16/10 em UTC, e a doacao de 15/10 vale, a de 16/10 nao."""
    from datetime import UTC, datetime

    from app.esquemas.doacao import DoacaoCriar

    usuario = await _usuario(sessao)
    hoje = hoje_na_ong(datetime(2026, 10, 16, 1, 0, tzinfo=UTC))
    dados = {"valor": Decimal("10"), "tipo": FrequenciaContribuicao.PONTUAL, "doador_nome": "A"}

    aceita = await servico_doacao.criar_doacao(
        sessao, DoacaoCriar(data=date(2026, 10, 15), **dados), usuario, hoje=hoje
    )
    assert aceita.data == date(2026, 10, 15)
    with pytest.raises(RegraNegocioError):
        await servico_doacao.criar_doacao(
            sessao, DoacaoCriar(data=date(2026, 10, 16), **dados), usuario, hoje=hoje
        )
