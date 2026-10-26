"""Fase 3, H11: portal publico de prestacao de contas (criterios em docs/HISTORIAS-FASE-3.md)."""

import inspect
from datetime import UTC, date, datetime, tzinfo
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tempo
from app.core.tempo import hoje_na_ong
from app.esquemas import publico
from app.main import app
from app.modelos.doacao import Doacao
from app.modelos.enums import CategoriaGasto, EspeciePet, FrequenciaContribuicao, PerfilUsuario
from app.modelos.gasto import Gasto
from app.modelos.padrinho import Padrinho
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.servicos import transparencia as servico_transparencia
from testes.conftest import cabecalho_do_perfil

# Dia fixo para as contas: o portal vai de novembro de 2025 a outubro de 2026.
HOJE = date(2026, 10, 20)


async def _usuario(sessao: AsyncSession) -> Usuario:
    usuario = Usuario(
        nome="Registradora Sigilosa",
        email="registradora@x.org",
        senha_hash="x",
        perfil=PerfilUsuario.VOLUNTARIO,
    )
    sessao.add(usuario)
    await sessao.commit()
    return usuario


async def _pet(sessao: AsyncSession, nome: str = "Rex") -> Pet:
    pet = Pet(nome=nome, especie=EspeciePet.CACHORRO, idade=2, data_resgate=date(2025, 1, 1))
    sessao.add(pet)
    await sessao.commit()
    return pet


async def _doacao(
    sessao: AsyncSession, valor: str, data: date, pet: Pet | None = None, **campos: Any
) -> Doacao:
    doacao = Doacao(
        valor=Decimal(valor),
        data=data,
        tipo=FrequenciaContribuicao.PONTUAL,
        doador_nome=campos.pop("doador_nome", "Doador"),
        pet_id=pet.id if pet else None,
        **campos,
    )
    sessao.add(doacao)
    await sessao.commit()
    return doacao


async def _gasto(
    sessao: AsyncSession,
    usuario: Usuario,
    valor: str,
    data: date,
    categoria: CategoriaGasto = CategoriaGasto.ALIMENTACAO,
    pet: Pet | None = None,
    **campos: Any,
) -> Gasto:
    gasto = Gasto(
        valor=Decimal(valor),
        data=data,
        categoria=categoria,
        descricao=campos.pop("descricao", "Racao"),
        pet_id=pet.id if pet else None,
        registrado_por_id=usuario.id,
        **campos,
    )
    sessao.add(gasto)
    await sessao.commit()
    return gasto


def _mes(portal: publico.PortalTransparencia, chave: str) -> publico.MesDoPortal:
    return next(mes for mes in portal.meses if mes.mes == chave)


# ------------------------------------------------------------------- H11.1


@pytest.mark.parametrize("perfil", [None, *PerfilUsuario])
async def test_portal_abre_sem_login_e_para_todos_os_perfis(
    client: AsyncClient, sessao: AsyncSession, perfil: PerfilUsuario | None
) -> None:
    cabecalho = await cabecalho_do_perfil(sessao, perfil) if perfil else {}
    resposta = await client.get("/transparencia", headers=cabecalho)
    assert resposta.status_code == 200, resposta.text


async def test_token_invalido_nao_atrapalha_o_portal(client: AsyncClient) -> None:
    """Quem tem um token vencido guardado no navegador continua vendo o portal."""
    resposta = await client.get("/transparencia", headers={"Authorization": "Bearer vencido"})
    assert resposta.status_code == 200


def test_rotas_publicas_sao_so_as_previstas() -> None:
    """Rota nova esquecida sem requer_perfil ficaria aberta sem ninguem notar. Este teste pega."""
    publicas = {
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        for metodo, operacao in operacoes.items()
        if not operacao.get("security")
    }
    assert publicas == {("POST", "/auth/login"), ("GET", "/saude"), ("GET", "/transparencia")}


# ------------------------------------------------------------------- H11.2


async def test_doze_meses_com_o_atual_em_andamento(sessao: AsyncSession) -> None:
    portal = await servico_transparencia.montar_portal(sessao, hoje=HOJE)

    assert [mes.mes for mes in portal.meses][:3] == ["2026-10", "2026-09", "2026-08"]
    assert len(portal.meses) == 12
    assert portal.meses[-1].mes == "2025-11"
    assert (portal.mes_inicial, portal.mes_final) == ("2025-11", "2026-10")
    assert [mes.em_andamento for mes in portal.meses] == [True] + [False] * 11
    # Sem lancamento nenhum, tudo zero, e nao vazio ou nulo.
    assert all(mes.arrecadado == mes.gasto == mes.saldo_acumulado == 0 for mes in portal.meses)


async def test_virada_do_ano(sessao: AsyncSession) -> None:
    portal = await servico_transparencia.montar_portal(sessao, hoje=date(2027, 1, 5))
    assert [mes.mes for mes in portal.meses][:3] == ["2027-01", "2026-12", "2026-11"]
    assert portal.meses[-1].mes == "2026-02"


async def test_arrecadado_gasto_saldo_e_acumulado(sessao: AsyncSession) -> None:
    usuario = await _usuario(sessao)
    # Antes do periodo: nao aparece nos meses, mas entra no saldo acumulado.
    await _doacao(sessao, "1000.00", date(2024, 5, 1))
    await _gasto(sessao, usuario, "300.00", date(2025, 10, 31))
    await _doacao(sessao, "200.00", date(2026, 9, 1))
    await _doacao(sessao, "50.25", date(2026, 9, 30))
    await _gasto(sessao, usuario, "80.10", date(2026, 9, 15))
    await _doacao(sessao, "10.00", date(2026, 10, 1))
    await _gasto(sessao, usuario, "40.00", date(2026, 10, 20))

    portal = await servico_transparencia.montar_portal(sessao, hoje=HOJE)

    setembro = _mes(portal, "2026-09")
    assert (setembro.arrecadado, setembro.gasto, setembro.saldo) == (
        Decimal("250.25"),
        Decimal("80.10"),
        Decimal("170.15"),
    )
    assert setembro.saldo_acumulado == Decimal("870.15")  # 700 de antes + 170,15

    outubro = _mes(portal, "2026-10")
    assert (outubro.arrecadado, outubro.gasto, outubro.saldo) == (
        Decimal("10.00"),
        Decimal("40.00"),
        Decimal("-30.00"),
    )
    assert outubro.saldo_acumulado == portal.saldo_acumulado == Decimal("840.15")
    assert _mes(portal, "2026-08").saldo_acumulado == Decimal("700.00")
    assert portal.arrecadado_no_periodo == Decimal("260.25")
    assert portal.gasto_no_periodo == Decimal("120.10")


async def test_lancamento_de_data_futura_fica_de_fora(sessao: AsyncSession) -> None:
    """A v1.0 aceitava doacao com data futura; ela nao entra antes de acontecer."""
    usuario = await _usuario(sessao)
    rex = await _pet(sessao)
    await _doacao(sessao, "500.00", date(2026, 11, 1), rex)
    await _gasto(sessao, usuario, "70.00", date(2026, 11, 1), pet=rex)

    portal = await servico_transparencia.montar_portal(sessao, hoje=HOJE)

    assert portal.arrecadado_no_periodo == portal.gasto_no_periodo == portal.saldo_acumulado == 0
    assert portal.pets == []


async def test_mes_e_o_de_brasilia(
    client: AsyncClient, sessao: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """28/02 as 22h em Brasilia ja e 01/03 em UTC: o mes em andamento e fevereiro (A-06).

    Data longe de hoje de proposito: uma rota que ignorasse hoje_na_ong tambem falharia.
    """

    class RelogioCongelado(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "RelogioCongelado":
            return cls(2027, 3, 1, 1, 0, tzinfo=UTC)

    monkeypatch.setattr(tempo, "datetime", RelogioCongelado)
    await _doacao(sessao, "33.00", date(2027, 2, 28))

    corpo = (await client.get("/transparencia")).json()

    assert corpo["mes_final"] == "2027-02"
    assert corpo["meses"][0]["mes"] == "2027-02"
    assert corpo["meses"][0]["em_andamento"] is True
    assert corpo["meses"][0]["arrecadado"] == "33.00"


async def test_mes_nao_depende_do_fuso_da_sessao_do_banco(sessao: AsyncSession) -> None:
    """Primeiro e ultimo dia do mes caem no mes certo mesmo com o banco em outro fuso."""
    await _doacao(sessao, "1.00", date(2026, 10, 1))
    await _doacao(sessao, "2.00", date(2026, 10, 31))
    await _doacao(sessao, "4.00", date(2026, 9, 30))
    for fuso in ("Pacific/Kiritimati", "Pacific/Pago_Pago"):
        await sessao.execute(text(f"SET LOCAL TIME ZONE '{fuso}'"))
        portal = await servico_transparencia.montar_portal(sessao, hoje=HOJE)
        assert _mes(portal, "2026-10").arrecadado == Decimal("3.00"), fuso
        assert _mes(portal, "2026-09").arrecadado == Decimal("4.00"), fuso


# ------------------------------------------------------------------- H11.3


async def test_gastos_do_mes_por_categoria(sessao: AsyncSession) -> None:
    usuario = await _usuario(sessao)
    vet = CategoriaGasto.VETERINARIO_MEDICAMENTOS
    await _gasto(sessao, usuario, "30.00", date(2026, 9, 2))
    await _gasto(sessao, usuario, "20.00", date(2026, 9, 3))
    await _gasto(sessao, usuario, "150.00", date(2026, 9, 4), vet)
    await _gasto(sessao, usuario, "9.99", date(2026, 10, 4), CategoriaGasto.TRANSPORTE)

    portal = await servico_transparencia.montar_portal(sessao, hoje=HOJE)

    setembro = _mes(portal, "2026-09")
    assert [(item.categoria, item.valor) for item in setembro.gastos_por_categoria] == [
        (vet, Decimal("150.00")),
        (CategoriaGasto.ALIMENTACAO, Decimal("50.00")),
    ]
    assert sum(item.valor for item in setembro.gastos_por_categoria) == setembro.gasto
    assert [item.categoria for item in _mes(portal, "2026-10").gastos_por_categoria] == [
        CategoriaGasto.TRANSPORTE
    ]
    assert _mes(portal, "2026-08").gastos_por_categoria == []


# ------------------------------------------------------------------- H11.4


async def test_por_pet_so_quem_teve_movimento_no_periodo(sessao: AsyncSession) -> None:
    usuario = await _usuario(sessao)
    rex = await _pet(sessao, "Rex")
    mia = await _pet(sessao, "Mia")
    antigo = await _pet(sessao, "Antigo")
    await _pet(sessao, "Parado")
    await _doacao(sessao, "100.00", date(2026, 9, 1), rex)
    await _doacao(sessao, "25.00", date(2026, 10, 1), rex)
    await _gasto(sessao, usuario, "60.00", date(2026, 9, 5), pet=rex)
    await _gasto(sessao, usuario, "45.50", date(2026, 10, 5), pet=mia)
    await _doacao(sessao, "999.00", date(2025, 10, 31), antigo)  # antes do periodo
    await _doacao(sessao, "70.00", date(2026, 9, 1))  # doacao geral, sem pet

    portal = await servico_transparencia.montar_portal(sessao, hoje=HOJE)

    assert [(pet.nome, pet.arrecadado, pet.gasto) for pet in portal.pets] == [
        ("Mia", Decimal("0.00"), Decimal("45.50")),
        ("Rex", Decimal("125.00"), Decimal("60.00")),
    ]
    assert [pet.pet_id for pet in portal.pets] == [mia.id, rex.id]


async def test_pets_de_mesmo_nome_nao_se_misturam(sessao: AsyncSession) -> None:
    primeiro = await _pet(sessao, "Bob")
    segundo = await _pet(sessao, "Bob")
    await _doacao(sessao, "10.00", date(2026, 10, 1), primeiro)
    await _doacao(sessao, "20.00", date(2026, 10, 1), segundo)

    portal = await servico_transparencia.montar_portal(sessao, hoje=HOJE)

    assert [(pet.pet_id, pet.arrecadado) for pet in portal.pets] == [
        (primeiro.id, Decimal("10.00")),
        (segundo.id, Decimal("20.00")),
    ]


# ------------------------------------------------------------------- H11.5


_CAMPOS = {
    "portal": {
        "mes_inicial",
        "mes_final",
        "arrecadado_no_periodo",
        "gasto_no_periodo",
        "saldo_acumulado",
        "meses",
        "pets",
    },
    "mes": {
        "mes",
        "em_andamento",
        "arrecadado",
        "gasto",
        "saldo",
        "saldo_acumulado",
        "gastos_por_categoria",
    },
    "categoria": {"categoria", "valor"},
    "pet": {"pet_id", "nome", "arrecadado", "gasto"},
}


async def test_nada_alem_do_previsto_sai_no_portal(
    client: AsyncClient, sessao: AsyncSession
) -> None:
    usuario = await _usuario(sessao)
    rex = await _pet(sessao)
    padrinho = Padrinho(
        nome="Beatriz Sigilosa", cpf="52998224725", email="beatriz@x.org", telefone="47999990000"
    )
    sessao.add(padrinho)
    await sessao.commit()
    doacao = await _doacao(
        sessao, "90.00", hoje_na_ong(), rex, doador_nome=None, padrinho_id=padrinho.id
    )
    await _doacao(
        sessao,
        "-90.00",
        hoje_na_ong(),
        rex,
        doador_nome=None,
        padrinho_id=padrinho.id,
        estorno_de_id=doacao.id,
        motivo_estorno="Motivo sigiloso",
    )
    await _doacao(sessao, "15.00", hoje_na_ong(), doador_nome="Carlos Avulso")
    await _gasto(
        sessao,
        usuario,
        "200.00",
        hoje_na_ong(),
        CategoriaGasto.VETERINARIO_MEDICAMENTOS,
        rex,
        descricao="Consulta com a Dra. Fulana",
    )

    resposta = await client.get("/transparencia")
    corpo = resposta.json()

    assert set(corpo) == _CAMPOS["portal"]
    for mes in corpo["meses"]:
        assert set(mes) == _CAMPOS["mes"]
        for categoria in mes["gastos_por_categoria"]:
            assert set(categoria) == _CAMPOS["categoria"]
    assert corpo["pets"]
    for pet in corpo["pets"]:
        assert set(pet) == _CAMPOS["pet"]

    for sigiloso in (
        "Beatriz",
        "52998224725",
        "beatriz@x.org",
        "47999990000",
        "Carlos Avulso",
        "Fulana",
        "Motivo sigiloso",
        "Registradora",
        "registradora@x.org",
    ):
        assert sigiloso not in resposta.text


def test_schemas_publicos_nao_herdam_dos_internos() -> None:
    """Campo novo num schema interno nao pode aparecer no portal sem ninguem decidir."""
    for _, classe in inspect.getmembers(publico, inspect.isclass):
        if not issubclass(classe, BaseModel) or classe.__module__ != publico.__name__:
            continue
        for base in classe.__mro__[1:]:
            if issubclass(base, BaseModel) and base is not BaseModel:
                assert base.__module__ == publico.__name__, f"{classe.__name__} herda {base}"


# ------------------------------------------------------------------- H11.6


async def test_estorno_entra_no_mes_em_que_foi_feito(sessao: AsyncSession) -> None:
    usuario = await _usuario(sessao)
    rex = await _pet(sessao)
    vet = CategoriaGasto.VETERINARIO_MEDICAMENTOS
    gasto = await _gasto(sessao, usuario, "100.00", date(2026, 9, 10), vet, rex)
    doacao = await _doacao(sessao, "40.00", date(2026, 9, 11), rex)
    antes = await servico_transparencia.montar_portal(sessao, hoje=date(2026, 9, 30))

    await _gasto(
        sessao,
        usuario,
        "-100.00",
        date(2026, 10, 2),
        vet,
        rex,
        estorno_de_id=gasto.id,
        motivo_estorno="Lancado em dobro",
    )
    await _doacao(
        sessao,
        "-40.00",
        date(2026, 10, 3),
        rex,
        estorno_de_id=doacao.id,
        motivo_estorno="Pix devolvido",
    )
    depois = await servico_transparencia.montar_portal(sessao, hoje=HOJE)

    # O mes fechado nao muda.
    assert _mes(depois, "2026-09") == _mes(antes, "2026-09").model_copy(
        update={"em_andamento": False}
    )
    outubro = _mes(depois, "2026-10")
    assert (outubro.arrecadado, outubro.gasto) == (Decimal("-40.00"), Decimal("-100.00"))
    assert [(item.categoria, item.valor) for item in outubro.gastos_por_categoria] == [
        (vet, Decimal("-100.00"))
    ]
    assert depois.saldo_acumulado == 0
    assert [(pet.nome, pet.arrecadado, pet.gasto) for pet in depois.pets] == [
        ("Rex", Decimal("0.00"), Decimal("0.00"))
    ]


# ------------------------------------------------------------------- H11.7


async def test_valores_saem_com_duas_casas_em_texto(
    client: AsyncClient, sessao: AsyncSession
) -> None:
    """Decimal vira texto no JSON: o navegador so formata, sem conta em ponto flutuante."""
    await _doacao(sessao, "0.10", hoje_na_ong())
    await _doacao(sessao, "0.20", hoje_na_ong())

    corpo = (await client.get("/transparencia")).json()

    assert corpo["meses"][0]["arrecadado"] == "0.30"
    assert corpo["saldo_acumulado"] == "0.30"
    assert corpo["meses"][1]["arrecadado"] == "0.00"
