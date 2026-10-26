"""Regras de negocio de Doacao (RF12, RF13, RN05; estornos na fase 3, H9)."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.doacao import DoacaoCriar
from app.esquemas.gasto import EstornoCriar
from app.modelos.doacao import Doacao
from app.modelos.usuario import Usuario
from app.repositorios import doacao as repo_doacao
from app.repositorios import padrinho as repo_padrinho
from app.repositorios import pet as repo_pet
from app.servicos.estorno import conferir_estornavel, gravar_com_auditoria


async def criar_doacao(
    sessao: AsyncSession, dados: DoacaoCriar, usuario: Usuario, hoje: date
) -> Doacao:
    """`hoje` e o dia em Brasilia (hoje_na_ong). Doacao e recebimento: nao tem data futura.
    Com data futura, o portal mostraria dinheiro num mes que ainda nao chegou, e o estorno
    dela sairia datado antes dela."""
    if dados.data > hoje:
        raise RegraNegocioError("A data da doacao nao pode estar no futuro.")
    if dados.padrinho_id is not None:
        padrinho = await repo_padrinho.obter_por_id(sessao, dados.padrinho_id)
        if padrinho is None:
            raise RecursoNaoEncontradoError(f"Padrinho {dados.padrinho_id} nao encontrado.")
    if dados.pet_id is not None and await repo_pet.obter_por_id(sessao, dados.pet_id) is None:
        raise RecursoNaoEncontradoError(f"Pet {dados.pet_id} nao encontrado.")

    # RN05 (valor > 0) e garantida pelo schema e pelo CHECK no banco.
    doacao = Doacao(**dados.model_dump(), registrado_por_id=usuario.id)
    await gravar_com_auditoria(sessao, doacao, usuario=usuario, entidade="doacao", acao="registro")
    return await _com_nomes(sessao, doacao.id)


async def estornar(
    sessao: AsyncSession, doacao_id: int, dados: EstornoCriar, usuario: Usuario, hoje: date
) -> Doacao:
    """Mesma regra do estorno de gasto (D13): negativo, com a data de hoje, ligado a original."""
    original = await repo_doacao.obter_com_lock(sessao, doacao_id)
    if original is None:
        raise RecursoNaoEncontradoError(f"Doacao {doacao_id} nao encontrada.")
    conferir_estornavel(original, await repo_doacao.tem_estorno(sessao, original.id))

    estorno = Doacao(
        padrinho_id=original.padrinho_id,
        pet_id=original.pet_id,
        doador_nome=original.doador_nome,
        valor=-original.valor,
        data=hoje,
        tipo=original.tipo,
        registrado_por_id=usuario.id,
        estorno_de_id=original.id,
        motivo_estorno=dados.motivo,
    )
    await gravar_com_auditoria(
        sessao, estorno, usuario=usuario, entidade="doacao", acao="estorno", antes=original
    )
    return await _com_nomes(sessao, estorno.id)


async def listar_doacoes(
    sessao: AsyncSession, pagina: int, tamanho_pagina: int, padrinho_id: int | None = None
) -> tuple[list[Doacao], int]:
    return await repo_doacao.listar(sessao, pagina, tamanho_pagina, padrinho_id)


async def _com_nomes(sessao: AsyncSession, doacao_id: int) -> Doacao:
    doacao = await repo_doacao.obter(sessao, doacao_id)
    assert doacao is not None  # acabou de ser gravada nesta sessao
    return doacao
