"""DEF-15: numero fora do intervalo do banco responde 422, nao 500 nem arredondamento calado.

Acima do maior INTEGER do Postgres, o banco recusava a consulta e a API respondia 500 -- em
id no caminho, na consulta e no corpo, e na pagina das listagens. O valor da doacao acima de
Numeric(10, 2) tambem dava 500, e com 3 casas era gravado arredondado.
"""

import importlib
import pkgutil
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import BaseModel

import app.esquemas
from app.esquemas.comuns import MAIOR_INTEIRO_DO_BANCO
from app.main import app as aplicacao

ACIMA = MAIOR_INTEIRO_DO_BANCO + 1


def _eh_inteiro(esquema: dict[str, Any]) -> bool:
    tipos = [esquema.get("type")] + [opcao.get("type") for opcao in esquema.get("anyOf", [])]
    return "integer" in tipos


def _maximo(esquema: dict[str, Any]) -> float | None:
    for opcao in [esquema, *esquema.get("anyOf", [])]:
        if "maximum" in opcao:
            return opcao["maximum"]
    return None


def _modelos_de_entrada() -> dict[str, type[BaseModel]]:
    """Os schemas que a API recebe no corpo, achados pelo contrato publicado."""
    contrato = aplicacao.openapi()
    nomes = set()
    for operacoes in contrato["paths"].values():
        for operacao in operacoes.values():
            for conteudo in operacao.get("requestBody", {}).get("content", {}).values():
                referencia = conteudo["schema"].get("$ref", "")
                if referencia:
                    nomes.add(referencia.rsplit("/", 1)[-1])

    modelos: dict[str, type[BaseModel]] = {}
    for modulo in pkgutil.iter_modules(app.esquemas.__path__):
        carregado = importlib.import_module(f"app.esquemas.{modulo.name}")
        for nome in nomes:
            classe = getattr(carregado, nome, None)
            if isinstance(classe, type) and issubclass(classe, BaseModel):
                modelos[nome] = classe
    return modelos


# ---------------------------------------------------------------- contrato


def test_todo_inteiro_que_entra_tem_limite() -> None:
    """Guarda para o futuro: rota nova com id sem limite volta a dar 500. Este teste pega."""
    contrato = aplicacao.openapi()
    sem_limite = []

    for caminho, operacoes in contrato["paths"].items():
        for metodo, operacao in operacoes.items():
            for parametro in operacao.get("parameters", []):
                esquema = parametro["schema"]
                if _eh_inteiro(esquema) and _maximo(esquema) is None:
                    sem_limite.append(f"{metodo.upper()} {caminho} ?{parametro['name']}")

    componentes = contrato["components"]["schemas"]
    for nome in _modelos_de_entrada():
        for campo, esquema in componentes[nome].get("properties", {}).items():
            if _eh_inteiro(esquema) and _maximo(esquema) is None:
                sem_limite.append(f"{nome}.{campo}")

    assert sem_limite == [], "numeros sem limite: use app/rotas/parametros.py ou IdNoCorpo"


def test_todo_inteiro_que_entra_cabe_no_banco() -> None:
    contrato = aplicacao.openapi()
    for operacoes in contrato["paths"].values():
        for operacao in operacoes.values():
            for parametro in operacao.get("parameters", []):
                maximo = _maximo(parametro["schema"])
                assert maximo is None or maximo <= MAIOR_INTEIRO_DO_BANCO, parametro["name"]


def test_todo_decimal_que_entra_tem_digitos_e_casas() -> None:
    """O OpenAPI nao mostra max_digits; o modelo, sim."""
    for nome, modelo in _modelos_de_entrada().items():
        for campo, info in modelo.model_fields.items():
            if info.annotation is Decimal:
                digitos = any(getattr(item, "max_digits", None) for item in info.metadata)
                casas = any(getattr(item, "decimal_places", None) for item in info.metadata)
                assert digitos and casas, f"{nome}.{campo} sem max_digits ou decimal_places"


# ------------------------------------------------------------ comportamento


@pytest.mark.parametrize(
    ("metodo", "url", "corpo"),
    [
        ("GET", f"/pets/{ACIMA}", None),
        ("GET", f"/adotantes/{ACIMA}", None),
        ("GET", f"/processos-adocao/{ACIMA}", None),
        ("GET", f"/pets?pagina={ACIMA}", None),
        ("GET", "/pets?pagina=99999999999999999999", None),
        ("GET", f"/processos-adocao?pet_id={ACIMA}", None),
        ("GET", f"/doacoes?padrinho_id={ACIMA}", None),
        ("POST", "/processos-adocao", {"pet_id": ACIMA, "adotante_id": 1}),
        (
            "POST",
            "/doacoes",
            {"valor": "10", "data": "2026-10-01", "tipo": "pontual", "padrinho_id": ACIMA},
        ),
    ],
)
async def test_id_e_pagina_acima_do_banco_respondem_422(
    client: AsyncClient, cabecalho_admin: dict, metodo: str, url: str, corpo: dict | None
) -> None:
    resposta = await client.request(metodo, url, json=corpo, headers=cabecalho_admin)
    assert resposta.status_code == 422, resposta.text


@pytest.mark.parametrize("pet_id", [0, -1])
async def test_id_zero_ou_negativo_continua_404(
    client: AsyncClient, cabecalho_admin: dict, pet_id: int
) -> None:
    """So o teto e novo: o comportamento de antes para ids que cabem no banco nao muda."""
    resposta = await client.get(f"/pets/{pet_id}", headers=cabecalho_admin)
    assert resposta.status_code == 404


async def test_o_proprio_maior_inteiro_ainda_vale(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    """A fronteira: o maior INTEGER e um id possivel. Nao existe, entao 404 -- nao 422."""
    resposta = await client.get(f"/pets/{MAIOR_INTEIRO_DO_BANCO}", headers=cabecalho_admin)
    assert resposta.status_code == 404


@pytest.mark.parametrize(
    ("valor", "status"),
    [
        ("10.123", 422),  # gravava 10.12, calado
        ("100000000", 422),  # nao cabe em Numeric(10, 2): dava 500
        ("99999999.99", 201),  # o maior que cabe
        ("0.01", 201),
        ("10.5", 201),
    ],
)
async def test_valor_da_doacao_cabe_no_banco_sem_arredondar(
    client: AsyncClient, cabecalho_admin: dict, valor: str, status: int
) -> None:
    resposta = await client.post(
        "/doacoes",
        json={"valor": valor, "data": "2026-10-01", "tipo": "pontual", "doador_nome": "Ana"},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == status, resposta.text
    if status == 201:
        assert Decimal(resposta.json()["valor"]) == Decimal(valor)


@pytest.mark.parametrize("valor", [10.1, 0.1, 0.3, 19.99, 99999999.99])
async def test_valor_enviado_como_numero_json_nao_esbarra_nas_casas(
    client: AsyncClient, cabecalho_admin: dict, valor: float
) -> None:
    """O painel manda o valor como numero JSON. 10.1 em binario e 10.0999...; o Pydantic
    converte pelo texto e passa. Se isso mudar numa atualizacao, toda doacao da tela
    passaria a ser recusada -- este teste avisa antes."""
    resposta = await client.post(
        "/doacoes",
        json={"valor": valor, "data": "2026-10-01", "tipo": "pontual", "doador_nome": "Ana"},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 201, resposta.text
    assert Decimal(resposta.json()["valor"]) == Decimal(str(valor))
