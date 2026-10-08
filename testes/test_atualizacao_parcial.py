"""PATCH com null nao pode chegar ao banco (DEF-14).

Os schemas de atualizacao parcial aceitam None para dizer "campo nao enviado". Enviado
como null, o valor ia direto para uma coluna NOT NULL e a atualizacao respondia 500.
"""

import pytest
from httpx import AsyncClient

_CASOS = {
    "pets": (
        {"nome": "Rex", "especie": "cachorro", "idade": 3, "data_resgate": "2025-01-10"},
        ("nome", "especie", "idade", "data_resgate"),
        {"nome": "Rex Atualizado"},
    ),
    "padrinhos": (
        {
            "nome": "Joao Lima",
            "cpf": "52998224725",
            "email": "j@teste.com",
            "telefone": "47999990000",
        },
        ("nome", "email", "telefone"),
        {"telefone": "47988887777"},
    ),
    "adotantes": (
        {
            "nome": "Maria Souza",
            "cpf": "12345678909",
            "email": "m@teste.com",
            "telefone": "47999990000",
            "endereco": "Rua das Flores, 10",
        },
        ("nome", "email", "telefone", "endereco", "ativo"),
        {"endereco": "Rua Nova, 20"},
    ),
}


async def _criar(client: AsyncClient, cabecalho: dict, recurso: str) -> dict:
    resposta = await client.post(f"/{recurso}", json=_CASOS[recurso][0], headers=cabecalho)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.mark.parametrize(
    ("recurso", "campo"),
    [(recurso, campo) for recurso, (_, campos, _) in _CASOS.items() for campo in campos],
)
async def test_patch_com_nulo_responde_422_e_nao_altera(
    client: AsyncClient, cabecalho_admin: dict, recurso: str, campo: str
) -> None:
    registro = await _criar(client, cabecalho_admin, recurso)

    resposta = await client.patch(
        f"/{recurso}/{registro['id']}", json={campo: None}, headers=cabecalho_admin
    )
    depois = await client.get(f"/{recurso}/{registro['id']}", headers=cabecalho_admin)

    assert resposta.status_code == 422
    assert depois.json()[campo] == registro[campo]


@pytest.mark.parametrize("recurso", list(_CASOS))
async def test_patch_parcial_continua_alterando_so_o_que_foi_enviado(
    client: AsyncClient, cabecalho_admin: dict, recurso: str
) -> None:
    """Controle: a correcao nao pode atrapalhar a atualizacao parcial normal."""
    registro = await _criar(client, cabecalho_admin, recurso)
    alteracao = _CASOS[recurso][2]

    resposta = await client.patch(
        f"/{recurso}/{registro['id']}", json=alteracao, headers=cabecalho_admin
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    for campo, valor in alteracao.items():
        assert corpo[campo] == valor
    for campo in _CASOS[recurso][1]:
        if campo not in alteracao:
            assert corpo[campo] == registro[campo]


async def test_contrato_nao_anuncia_nulo_nos_campos_que_recusam_nulo(client: AsyncClient) -> None:
    """O Swagger dizia que os campos aceitavam null, mas a API recusa com 422: quem gerasse
    um cliente pelo contrato mandaria null."""
    esquemas = (await client.get("/openapi.json")).json()["components"]["schemas"]

    for nome in ("PetAtualizar", "PadrinhoAtualizar", "AdotanteAtualizar"):
        for campo, propriedade in esquemas[nome]["properties"].items():
            tipos = [opcao.get("type") for opcao in propriedade.get("anyOf", [propriedade])]
            assert "null" not in tipos, f"{nome}.{campo}"
            assert propriedade.get("default", "ausente") is not None, f"{nome}.{campo}"
