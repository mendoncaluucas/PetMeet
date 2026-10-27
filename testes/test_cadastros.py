"""Testes de cadastro de pessoas: validacao de CPF e duplicidade (DEF-08, DEF-12)."""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RegraNegocioError
from app.core.seguranca import gerar_hash_senha
from app.esquemas.adotante import AdotanteCriar
from app.esquemas.padrinho import PadrinhoCriar
from app.esquemas.usuario import UsuarioCriar
from app.modelos.adotante import Adotante
from app.modelos.enums import PerfilUsuario
from app.modelos.padrinho import Padrinho
from app.modelos.usuario import Usuario
from app.servicos import adotante as servico_adotante
from app.servicos import padrinho as servico_padrinho
from app.servicos import usuario as servico_usuario
from testes.conftest import FabricaSessaoTeste, esperar_conexoes_bloqueadas

CPF_VALIDO = "52998224725"


def _adotante(cpf: str) -> dict:
    return {
        "nome": "Maria Souza",
        "cpf": cpf,
        "email": "maria@teste.com",
        "telefone": "47999990000",
        "endereco": "Rua das Flores, 10",
    }


async def test_cpf_com_pontuacao_e_aceito_e_gravado_so_com_digitos(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    resposta = await client.post(
        "/adotantes", json=_adotante("529.982.247-25"), headers=cabecalho_admin
    )

    assert resposta.status_code == 201
    assert resposta.json()["cpf"] == CPF_VALIDO


@pytest.mark.parametrize(
    "cpf",
    [
        "088.888.888-88",  # primeiro digito verificador deveria ser 0
        "52998224726",  # segundo digito verificador deveria ser 5
        "111.111.111-11",  # digitos repetidos passam na conta, mas nao sao CPF
        "00000000000",
    ],
)
async def test_cpf_invalido_e_rejeitado(
    client: AsyncClient, cabecalho_admin: dict, cpf: str
) -> None:
    resposta = await client.post("/adotantes", json=_adotante(cpf), headers=cabecalho_admin)
    assert resposta.status_code == 422


async def test_padrinho_tem_a_mesma_validacao_de_cpf(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    padrinho = {"nome": "Joao Lima", "email": "joao@teste.com", "telefone": "47999990000"}

    invalido = await client.post(
        "/padrinhos", json={**padrinho, "cpf": "088.888.888-88"}, headers=cabecalho_admin
    )
    valido = await client.post(
        "/padrinhos", json={**padrinho, "cpf": "529.982.247-25"}, headers=cabecalho_admin
    )

    assert invalido.status_code == 422
    assert valido.status_code == 201


async def test_cpf_duplicado_em_sequencia_e_rejeitado(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    await client.post("/adotantes", json=_adotante(CPF_VALIDO), headers=cabecalho_admin)
    resposta = await client.post("/adotantes", json=_adotante(CPF_VALIDO), headers=cabecalho_admin)
    assert resposta.status_code == 422


async def test_listagem_com_cpf_antigo_fora_da_regra_continua_funcionando(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    """A-03: a regra nova vale no cadastro, nao na leitura do que ja esta gravado."""
    sessao.add(Adotante(**_adotante("11111111111")))
    await sessao.commit()

    resposta = await client.get("/adotantes", headers=cabecalho_admin)

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1


def _caso_adotante():
    ja_gravado = Adotante(**_adotante(CPF_VALIDO))
    return ja_gravado, servico_adotante.criar_adotante, AdotanteCriar(**_adotante(CPF_VALIDO))


def _caso_padrinho():
    dados = {
        "nome": "Joao Lima",
        "cpf": CPF_VALIDO,
        "email": "joao@teste.com",
        "telefone": "47999990000",
    }
    return Padrinho(**dados), servico_padrinho.criar_padrinho, PadrinhoCriar(**dados)


def _caso_usuario():
    ja_gravado = Usuario(
        nome="Ana",
        email="ana@teste.com",
        senha_hash=gerar_hash_senha("senha-segura-1"),
        perfil=PerfilUsuario.VOLUNTARIO,
    )
    dados = UsuarioCriar(
        nome="Ana", email="ana@teste.com", senha="senha-segura-1", perfil=PerfilUsuario.VOLUNTARIO
    )
    return ja_gravado, servico_usuario.criar_usuario, dados


@pytest.mark.parametrize("montar_caso", [_caso_adotante, _caso_padrinho, _caso_usuario])
async def test_cadastro_duplicado_simultaneo_recebe_a_resposta_do_caso_sequencial(
    montar_caso,
) -> None:
    """DEF-08: dois cadastros iguais ao mesmo tempo -- o segundo respondia 500.

    Deterministico: uma conexao grava o registro sem commit e segura a chave unica; o
    servico consulta, nao ve nada, e para no indice unico. So entao a primeira commita.
    """
    ja_gravado, criar, dados = montar_caso()

    async def _segundo_cadastro() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await criar(sessao_local, dados)

    async with FabricaSessaoTeste() as primeira:
        primeira.add(ja_gravado)
        await primeira.flush()
        tarefa = asyncio.create_task(_segundo_cadastro())
        await esperar_conexoes_bloqueadas(1)
        await primeira.commit()

    with pytest.raises(RegraNegocioError):
        await tarefa
