"""Fase 3, H10: esperado x recebido dos padrinhos (criterios em docs/HISTORIAS-FASE-3.md)."""

import itertools
import random
from datetime import UTC, date, datetime, timedelta, tzinfo
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tempo
from app.esquemas.apadrinhamento import EsperadoRecebido, SituacaoDoMes
from app.modelos.apadrinhamento import Apadrinhamento
from app.modelos.doacao import Doacao
from app.modelos.enums import EspeciePet, FrequenciaContribuicao
from app.modelos.padrinho import Padrinho
from app.modelos.pet import Pet
from app.servicos import esperado_recebido as servico

# Dia fixo para as contas: o periodo vai de novembro de 2025 a outubro de 2026.
HOJE = date(2026, 10, 20)
_CPFS = (f"{n:011d}" for n in itertools.count(20_000_000_000))

EM_DIA = SituacaoDoMes.EM_DIA
PARCIAL = SituacaoDoMes.PARCIAL
SEM_DOACAO = SituacaoDoMes.SEM_DOACAO
EM_ANDAMENTO = SituacaoDoMes.EM_ANDAMENTO
SEM_COMPROMISSO = SituacaoDoMes.SEM_COMPROMISSO


async def _padrinho(sessao: AsyncSession, nome: str = "Joana") -> Padrinho:
    padrinho = Padrinho(nome=nome, cpf=next(_CPFS), email="j@x.org", telefone="47999990000")
    sessao.add(padrinho)
    await sessao.commit()
    return padrinho


async def _pet(sessao: AsyncSession, nome: str = "Rex") -> Pet:
    pet = Pet(nome=nome, especie=EspeciePet.CACHORRO, idade=2, data_resgate=date(2025, 1, 1))
    sessao.add(pet)
    await sessao.commit()
    return pet


async def _apadrinhar(
    sessao: AsyncSession,
    padrinho: Padrinho,
    valor: str,
    inicio: date,
    fim: date | None = None,
    pet: Pet | None = None,
) -> Apadrinhamento:
    apadrinhamento = Apadrinhamento(
        padrinho_id=padrinho.id,
        pet_id=(pet or await _pet(sessao)).id,
        valor_mensal=Decimal(valor),
        data_inicio=inicio,
        data_fim=fim,
    )
    sessao.add(apadrinhamento)
    await sessao.commit()
    return apadrinhamento


async def _doar(
    sessao: AsyncSession, padrinho: Padrinho | None, valor: str, data: date, **campos: object
) -> Doacao:
    doacao = Doacao(
        padrinho_id=padrinho.id if padrinho else None,
        doador_nome=None if padrinho else "Avulso",
        valor=Decimal(valor),
        data=data,
        tipo=FrequenciaContribuicao.RECORRENTE,
        **campos,
    )
    sessao.add(doacao)
    await sessao.commit()
    return doacao


async def _listar(
    sessao: AsyncSession, hoje: date = HOJE, so_pendentes: bool = False, **pagina: int
) -> tuple[list[EsperadoRecebido], int]:
    return await servico.listar(
        sessao,
        hoje,
        pagina.get("pagina", 1),
        pagina.get("tamanho_pagina", 20),
        so_pendentes,
    )


def _mes(item: EsperadoRecebido, chave: str) -> tuple[Decimal, Decimal, Decimal, SituacaoDoMes]:
    mes = next(mes for mes in item.meses if mes.mes == chave)
    return mes.esperado, mes.recebido, mes.diferenca, mes.situacao


# ------------------------------------------------------------------- acesso


async def test_so_a_equipe_ve(
    client: AsyncClient, cabecalho_admin: dict, cabecalho_voluntario: dict
) -> None:
    for cabecalho in (cabecalho_admin, cabecalho_voluntario):
        resposta = await client.get("/apadrinhamentos/esperado-recebido", headers=cabecalho)
        assert resposta.status_code == 200, resposta.text
    assert (await client.get("/apadrinhamentos/esperado-recebido")).status_code == 401
    # O veterinario recebe 403: a rota fica fora da matriz dele (test_veterinario.py).


# ---------------------------------------------------------------- H10.1-3


async def test_esperado_recebido_diferenca_e_situacao(sessao: AsyncSession) -> None:
    joana = await _padrinho(sessao)
    await _apadrinhar(sessao, joana, "50.00", date(2026, 8, 15))
    await _apadrinhar(sessao, joana, "30.00", date(2026, 9, 1), fim=date(2026, 9, 10))
    await _doar(sessao, joana, "50.00", date(2026, 8, 31))
    await _doar(sessao, joana, "25.00", date(2026, 9, 2))
    await _doar(sessao, joana, "15.00", date(2026, 9, 28))

    [item], total = await _listar(sessao)

    assert total == 1
    assert (item.padrinho_id, item.padrinho_nome) == (joana.id, "Joana")
    assert _mes(item, "2026-08") == (Decimal("50.00"), Decimal("50.00"), Decimal("0.00"), EM_DIA)
    assert _mes(item, "2026-09") == (Decimal("80.00"), Decimal("40.00"), Decimal("-40.00"), PARCIAL)
    assert _mes(item, "2026-10") == (Decimal("50.00"), 0, Decimal("-50.00"), EM_ANDAMENTO)
    assert _mes(item, "2026-07") == (0, 0, 0, SEM_COMPROMISSO)
    assert item.meses_pendentes == 1


async def test_doze_meses_do_mais_recente_ao_mais_antigo(sessao: AsyncSession) -> None:
    await _apadrinhar(sessao, await _padrinho(sessao), "10.00", date(2025, 1, 1))

    [item], _ = await _listar(sessao)

    assert [mes.mes for mes in item.meses] == [
        "2026-10",
        "2026-09",
        "2026-08",
        "2026-07",
        "2026-06",
        "2026-05",
        "2026-04",
        "2026-03",
        "2026-02",
        "2026-01",
        "2025-12",
        "2025-11",
    ]
    assert [mes.situacao for mes in item.meses] == [EM_ANDAMENTO] + [SEM_DOACAO] * 11
    assert item.meses_pendentes == 11


async def test_conta_no_mes_se_esteve_ativo_em_algum_dia(sessao: AsyncSession) -> None:
    joana = await _padrinho(sessao)
    # Comeca no ultimo dia de julho e termina no primeiro de setembro: julho, agosto e
    # setembro contam inteiros.
    await _apadrinhar(sessao, joana, "20.00", date(2026, 7, 31), fim=date(2026, 9, 1))

    [item], _ = await _listar(sessao)

    esperados = {mes.mes: mes.esperado for mes in item.meses if mes.esperado}
    assert esperados == {"2026-07": 20, "2026-08": 20, "2026-09": 20}


async def test_estorno_desconta_no_mes_em_que_foi_feito(sessao: AsyncSession) -> None:
    joana = await _padrinho(sessao)
    await _apadrinhar(sessao, joana, "50.00", date(2026, 8, 1))
    doacao = await _doar(sessao, joana, "50.00", date(2026, 8, 5))
    await _doar(
        sessao,
        joana,
        "-50.00",
        date(2026, 9, 3),
        estorno_de_id=doacao.id,
        motivo_estorno="Pix devolvido",
    )

    [item], _ = await _listar(sessao)

    # Agosto, ja fechado, nao muda; o estorno entra em setembro, que fica negativo.
    assert _mes(item, "2026-08")[3] == EM_DIA
    assert _mes(item, "2026-09") == (
        Decimal("50.00"),
        Decimal("-50.00"),
        Decimal("-100.00"),
        SEM_DOACAO,
    )


async def test_mes_corrente_pago_ja_fica_em_dia(sessao: AsyncSession) -> None:
    joana = await _padrinho(sessao)
    await _apadrinhar(sessao, joana, "50.00", date(2026, 10, 1))
    await _doar(sessao, joana, "60.00", date(2026, 10, 2))

    [item], _ = await _listar(sessao)

    assert _mes(item, "2026-10") == (Decimal("50.00"), Decimal("60.00"), Decimal("10.00"), EM_DIA)
    assert item.meses_pendentes == 0


async def test_mes_corrente_nao_e_atraso(sessao: AsyncSession) -> None:
    joana = await _padrinho(sessao)
    await _apadrinhar(sessao, joana, "50.00", date(2026, 10, 1))
    await _doar(sessao, joana, "10.00", date(2026, 10, 2))

    [item], _ = await _listar(sessao)

    assert _mes(item, "2026-10")[3] == EM_ANDAMENTO
    assert item.meses_pendentes == 0
    assert (await _listar(sessao, so_pendentes=True)) == ([], 0)


async def test_so_contam_as_doacoes_do_proprio_padrinho(sessao: AsyncSession) -> None:
    joana = await _padrinho(sessao, "Joana")
    carlos = await _padrinho(sessao, "Carlos")
    await _apadrinhar(sessao, joana, "50.00", date(2026, 9, 1))
    await _doar(sessao, carlos, "500.00", date(2026, 9, 5))
    await _doar(sessao, None, "500.00", date(2026, 9, 5))

    itens, total = await _listar(sessao)

    # Carlos so doou, sem compromisso: nao entra na lista.
    assert total == 1
    assert _mes(itens[0], "2026-09")[1:] == (0, Decimal("-50.00"), SEM_DOACAO)


async def test_apadrinhamento_encerrado_antes_do_periodo_fica_de_fora(
    sessao: AsyncSession,
) -> None:
    joana = await _padrinho(sessao)
    await _apadrinhar(sessao, joana, "50.00", date(2024, 1, 1), fim=date(2025, 10, 31))
    assert await _listar(sessao) == ([], 0)

    # Um dia dentro do periodo ja basta.
    await _apadrinhar(sessao, joana, "50.00", date(2024, 1, 1), fim=date(2025, 11, 1))
    [item], _ = await _listar(sessao)
    assert _mes(item, "2025-11")[0] == Decimal("50.00")


# ------------------------------------------------------------------- H10.4


async def test_mes_e_o_de_brasilia(
    client: AsyncClient,
    sessao: AsyncSession,
    cabecalho_admin: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """28/02 as 22h em Brasilia ja e 01/03 em UTC: o mes em andamento e fevereiro (A-06)."""

    class RelogioCongelado(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "RelogioCongelado":
            return cls(2027, 3, 1, 1, 0, tzinfo=UTC)

    joana = await _padrinho(sessao)
    await _apadrinhar(sessao, joana, "50.00", date(2027, 2, 1))
    await _doar(sessao, joana, "50.00", date(2027, 2, 28))
    monkeypatch.setattr(tempo, "datetime", RelogioCongelado)

    resposta = await client.get("/apadrinhamentos/esperado-recebido", headers=cabecalho_admin)

    [fevereiro, janeiro, *_] = resposta.json()["itens"][0]["meses"]
    assert (fevereiro["mes"], fevereiro["recebido"], fevereiro["situacao"]) == (
        "2027-02",
        "50.00",
        "em_dia",
    )
    # Mes sem lancamento: zero com duas casas, como todo valor em dinheiro da API.
    assert (janeiro["esperado"], janeiro["recebido"], janeiro["diferenca"]) == (
        "0.00",
        "0.00",
        "0.00",
    )


# ------------------------------------------------------------------- H10.5-6


async def test_pendentes_primeiro_e_filtro(sessao: AsyncSession) -> None:
    for nome in ("Ana", "Bruno", "Carla"):
        padrinho = await _padrinho(sessao, nome)
        await _apadrinhar(sessao, padrinho, "10.00", date(2026, 9, 1))
        if nome != "Carla":
            await _doar(sessao, padrinho, "10.00", date(2026, 9, 1))

    itens, total = await _listar(sessao)
    assert total == 3
    assert [(item.padrinho_nome, item.meses_pendentes) for item in itens] == [
        ("Carla", 1),
        ("Ana", 0),
        ("Bruno", 0),
    ]

    itens, total = await _listar(sessao, so_pendentes=True)
    assert (total, [item.padrinho_nome for item in itens]) == (1, ["Carla"])


async def test_paginacao(sessao: AsyncSession) -> None:
    for nome in ("Ana", "Bruno", "Carla", "Davi", "Elis"):
        await _apadrinhar(sessao, await _padrinho(sessao, nome), "10.00", date(2026, 10, 1))

    primeira, total = await _listar(sessao, pagina=1, tamanho_pagina=2)
    terceira, _ = await _listar(sessao, pagina=3, tamanho_pagina=2)

    assert total == 5
    assert [item.padrinho_nome for item in primeira] == ["Ana", "Bruno"]
    assert [item.padrinho_nome for item in terceira] == ["Elis"]
    # Cada padrinho traz os proprios 12 meses, sem misturar com os da outra pagina.
    assert all(len(item.meses) == 12 for item in primeira + terceira)


async def test_padrinhos_de_mesmo_nome_nao_se_misturam(sessao: AsyncSession) -> None:
    primeira = await _padrinho(sessao, "Joana")
    segunda = await _padrinho(sessao, "Joana")
    await _apadrinhar(sessao, primeira, "10.00", date(2026, 9, 1))
    await _apadrinhar(sessao, segunda, "20.00", date(2026, 9, 1))
    await _doar(sessao, segunda, "20.00", date(2026, 9, 1))

    itens, _ = await _listar(sessao)

    assert [(item.padrinho_id, _mes(item, "2026-09")[3]) for item in itens] == [
        (primeira.id, SEM_DOACAO),
        (segunda.id, EM_DIA),
    ]


# --------------------------------------------------------- conferencia geral


async def test_bate_com_a_conta_feita_a_mao_em_dados_aleatorios(sessao: AsyncSession) -> None:
    """A grade do banco contra uma conta direta em Python, com datas quebradas no meio do
    mes, apadrinhamentos que comecam e terminam fora do periodo, doacoes e estornos."""
    sorteio = random.Random(20261026)
    dias = [date(2025, 6, 1) + timedelta(days=n) for n in range((HOJE - date(2025, 6, 1)).days)]
    padrinhos = [await _padrinho(sessao, f"Padrinho {n:02d}") for n in range(25)]
    apadrinhamentos: list[tuple[int, Decimal, date, date | None]] = []
    doacoes: list[tuple[int, Decimal, date]] = []
    for padrinho in padrinhos:
        for _ in range(sorteio.randint(0, 3)):
            inicio = sorteio.choice(dias)
            fim = sorteio.choice([None, *[dia for dia in dias if dia >= inicio][:200]])
            valor = Decimal(sorteio.randint(1, 9000)) / 100
            # Um pet para cada: o mesmo padrinho so tem um ativo por pet.
            await _apadrinhar(sessao, padrinho, str(valor), inicio, fim=fim)
            apadrinhamentos.append((padrinho.id, valor, inicio, fim))
        for _ in range(sorteio.randint(0, 15)):
            doacao = await _doar(
                sessao, padrinho, str(Decimal(sorteio.randint(1, 9000)) / 100), sorteio.choice(dias)
            )
            doacoes.append((padrinho.id, doacao.valor, doacao.data))
            if sorteio.random() < 0.2:
                dia = sorteio.choice([dia for dia in dias if dia >= doacao.data])
                await _doar(
                    sessao,
                    padrinho,
                    str(-doacao.valor),
                    dia,
                    estorno_de_id=doacao.id,
                    motivo_estorno="Teste",
                )
                doacoes.append((padrinho.id, -doacao.valor, dia))
    await sessao.commit()

    itens, total = await _listar(sessao, tamanho_pagina=100)

    meses = [tempo.intervalo_do_mes(mes) for mes in tempo.ultimos_meses(HOJE, 12)]
    esperado_por_padrinho = {}
    for padrinho in padrinhos:
        linhas = []
        for inicio, fim in reversed(meses):
            esperado = sum(
                (
                    valor
                    for dono, valor, comeco, termino in apadrinhamentos
                    if dono == padrinho.id
                    and comeco < fim
                    and (termino is None or termino >= inicio)
                ),
                Decimal("0.00"),
            )
            recebido = sum(
                (
                    valor
                    for dono, valor, dia in doacoes
                    if dono == padrinho.id and inicio <= dia < fim
                ),
                Decimal("0.00"),
            )
            linhas.append((inicio.strftime("%Y-%m"), esperado, recebido))
        if any(esperado for _, esperado, _ in linhas):
            esperado_por_padrinho[padrinho.id] = linhas

    assert total == len(esperado_por_padrinho) > 5
    assert any(termino is None for *_, termino in apadrinhamentos)
    calculado = {
        item.padrinho_id: [(mes.mes, mes.esperado, mes.recebido) for mes in item.meses]
        for item in itens
    }
    assert calculado == esperado_por_padrinho
