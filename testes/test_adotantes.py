"""Exclusao e inativacao de adotante (DEF-13)."""

import asyncio
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.adotante import AdotanteAtualizar
from app.esquemas.processo_adocao import ProcessoAdocaoCriar
from app.modelos.adotante import Adotante
from app.modelos.enums import StatusProcessoAdocao
from app.modelos.pet import Pet
from app.modelos.processo_adocao import ProcessoAdocao
from app.servicos import adotante as servico_adotante
from app.servicos import processo_adocao as servico_processo
from testes.conftest import FabricaSessaoTeste, esperar_conexoes_bloqueadas

CPF = "52998224725"


def _dados(cpf: str = CPF) -> dict:
    return {
        "nome": "Maria Souza",
        "cpf": cpf,
        "email": "maria@teste.com",
        "telefone": "47999990000",
        "endereco": "Rua das Flores, 10",
    }


async def _adotante(sessao: AsyncSession, **campos) -> Adotante:
    adotante = Adotante(**{**_dados(), **campos})
    sessao.add(adotante)
    await sessao.commit()
    await sessao.refresh(adotante)
    return adotante


async def _pet(sessao: AsyncSession) -> Pet:
    pet = Pet(nome="Tom", especie="gato", idade=2, data_resgate=date(2026, 8, 1))
    sessao.add(pet)
    await sessao.commit()
    await sessao.refresh(pet)
    return pet


async def test_excluir_adotante_sem_processo(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    adotante = await _adotante(sessao)

    resposta = await client.delete(f"/adotantes/{adotante.id}", headers=cabecalho_admin)

    assert resposta.status_code == 204
    busca = await client.get(f"/adotantes/{adotante.id}", headers=cabecalho_admin)
    assert busca.status_code == 404


async def test_excluir_adotante_com_processo_e_recusado(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    """O processo e historico de adocao: excluir o adotante apagaria de quem foi o pet."""
    adotante = await _adotante(sessao)
    pet = await _pet(sessao)
    sessao.add(
        ProcessoAdocao(
            pet_id=pet.id, adotante_id=adotante.id, status=StatusProcessoAdocao.CANCELADO
        )
    )
    await sessao.commit()

    resposta = await client.delete(f"/adotantes/{adotante.id}", headers=cabecalho_admin)

    assert resposta.status_code == 409
    assert "inative" in resposta.json()["detalhe"]


async def test_inativar_tira_o_adotante_da_listagem_padrao(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    adotante = await _adotante(sessao)

    resposta = await client.patch(
        f"/adotantes/{adotante.id}", json={"ativo": False}, headers=cabecalho_admin
    )
    padrao = await client.get("/adotantes", headers=cabecalho_admin)
    com_inativos = await client.get(
        "/adotantes", params={"incluir_inativos": True}, headers=cabecalho_admin
    )
    por_id = await client.get(f"/adotantes/{adotante.id}", headers=cabecalho_admin)

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False
    assert padrao.json()["total"] == 0
    assert com_inativos.json()["total"] == 1
    assert por_id.status_code == 200


async def test_adotante_inativo_nao_abre_processo(sessao: AsyncSession) -> None:
    adotante = await _adotante(sessao, ativo=False)
    pet = await _pet(sessao)

    with pytest.raises(RegraNegocioError, match="inativo"):
        await servico_processo.criar_processo_adocao(
            sessao, ProcessoAdocaoCriar(pet_id=pet.id, adotante_id=adotante.id), responsavel_id=None
        )


async def test_adotante_reativado_volta_a_abrir_processo(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    adotante = await _adotante(sessao, ativo=False)
    pet = await _pet(sessao)

    await client.patch(f"/adotantes/{adotante.id}", json={"ativo": True}, headers=cabecalho_admin)
    resposta = await client.post(
        "/processos-adocao",
        json={"pet_id": pet.id, "adotante_id": adotante.id},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 201


async def test_cadastro_com_cpf_de_adotante_inativo_orienta_reativar(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    await _adotante(sessao, ativo=False)

    resposta = await client.post("/adotantes", json=_dados(), headers=cabecalho_admin)

    assert resposta.status_code == 422
    assert "reative" in resposta.json()["detalhe"]


async def test_exclusao_que_chega_antes_da_abertura_de_processo(sessao: AsyncSession) -> None:
    """A exclusao trava o adotante primeiro: a abertura espera e encontra o adotante excluido.

    Sem a trava na abertura, ela lia o adotante antes da exclusao commitar, gravava o
    processo e quebrava na chave externa (reproduzido em 29/09).
    """
    adotante = await _adotante(sessao)
    pet = await _pet(sessao)

    async def _abrir() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_processo.criar_processo_adocao(
                sessao_local,
                ProcessoAdocaoCriar(pet_id=pet.id, adotante_id=adotante.id),
                responsavel_id=None,
            )

    async with FabricaSessaoTeste() as exclusao:
        await exclusao.execute(select(Adotante).where(Adotante.id == adotante.id).with_for_update())
        await exclusao.execute(text("DELETE FROM adotantes WHERE id = :id"), {"id": adotante.id})
        tarefa = asyncio.create_task(_abrir())
        await esperar_conexoes_bloqueadas(1)
        await exclusao.commit()

    with pytest.raises(RecursoNaoEncontradoError):
        await tarefa


async def test_abertura_de_processo_que_chega_antes_da_exclusao(sessao: AsyncSession) -> None:
    """A abertura trava o adotante primeiro: a exclusao espera e encontra o processo."""
    adotante = await _adotante(sessao)
    pet = await _pet(sessao)

    async with FabricaSessaoTeste() as abertura:
        await abertura.execute(
            select(Adotante).where(Adotante.id == adotante.id).with_for_update(read=True)
        )
        abertura.add(
            ProcessoAdocao(
                pet_id=pet.id, adotante_id=adotante.id, status=StatusProcessoAdocao.EM_ANALISE
            )
        )
        await abertura.flush()
        tarefa = asyncio.create_task(_excluir(adotante.id))
        await esperar_conexoes_bloqueadas(1)
        await abertura.commit()

    with pytest.raises(ConflitoError):
        await tarefa


async def _excluir(adotante_id: int) -> None:
    async with FabricaSessaoTeste() as sessao_local:
        await servico_adotante.excluir_adotante(sessao_local, adotante_id)


async def test_atualizar_com_nulo_e_recusado_em_vez_de_quebrar(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    """DEF-14: null ia direto para uma coluna NOT NULL e a atualizacao respondia 500."""
    adotante = await _adotante(sessao)

    for campo in ("nome", "ativo"):
        resposta = await client.patch(
            f"/adotantes/{adotante.id}", json={campo: None}, headers=cabecalho_admin
        )
        assert resposta.status_code == 422, campo


async def test_atualizacao_que_chega_depois_da_exclusao(sessao: AsyncSession) -> None:
    """Inativar (ou editar) um adotante que outra pessoa esta excluindo.

    Sem trava, a atualizacao lia o adotante, a exclusao commitava, e o UPDATE nao
    encontrava a linha: StaleDataError, respondido como 500 -- 18 de 20 rodadas no
    teste de estresse de 29/09.
    """
    adotante = await _adotante(sessao)

    async def _inativar() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_adotante.atualizar_adotante(
                sessao_local, adotante.id, AdotanteAtualizar(ativo=False)
            )

    async with FabricaSessaoTeste() as exclusao:
        await exclusao.execute(select(Adotante).where(Adotante.id == adotante.id).with_for_update())
        await exclusao.execute(text("DELETE FROM adotantes WHERE id = :id"), {"id": adotante.id})
        tarefa = asyncio.create_task(_inativar())
        await esperar_conexoes_bloqueadas(1)
        await exclusao.commit()

    with pytest.raises(RecursoNaoEncontradoError):
        await tarefa
