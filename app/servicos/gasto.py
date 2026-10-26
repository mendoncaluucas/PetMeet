"""Regras de gastos e estornos de gasto (fase 3, H9; decisoes D13 e D14)."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.gasto import EstornoCriar, GastoCriar
from app.modelos.enums import CategoriaGasto
from app.modelos.gasto import Gasto
from app.modelos.usuario import Usuario
from app.repositorios import gasto as repo_gasto
from app.repositorios import pet as repo_pet
from app.servicos.estorno import conferir_estornavel, gravar_com_auditoria


async def registrar(sessao: AsyncSession, dados: GastoCriar, usuario: Usuario, hoje: date) -> Gasto:
    """`hoje` e o dia em Brasilia (hoje_na_ong)."""
    if dados.data > hoje:
        raise RegraNegocioError("A data do gasto nao pode estar no futuro.")
    if dados.pet_id is not None and await repo_pet.obter_por_id(sessao, dados.pet_id) is None:
        raise RecursoNaoEncontradoError(f"Pet {dados.pet_id} nao encontrado.")

    gasto = Gasto(**dados.model_dump(), registrado_por_id=usuario.id)
    await gravar_com_auditoria(sessao, gasto, usuario=usuario, entidade="gasto", acao="registro")
    return await _com_nomes(sessao, gasto.id)


async def estornar(
    sessao: AsyncSession, gasto_id: int, dados: EstornoCriar, usuario: Usuario, hoje: date
) -> Gasto:
    """Lancamento negativo com a data de hoje, ligado ao original (D13). O mes do original
    nao muda: o estorno sai dos totais no mes em que foi feito."""
    # Trava o original: dois estornos ao mesmo tempo nao passam os dois pela conferencia.
    original = await repo_gasto.obter_com_lock(sessao, gasto_id)
    if original is None:
        raise RecursoNaoEncontradoError(f"Gasto {gasto_id} nao encontrado.")
    conferir_estornavel(original, await repo_gasto.tem_estorno(sessao, original.id))

    estorno = Gasto(
        valor=-original.valor,
        data=hoje,
        categoria=original.categoria,
        descricao=original.descricao,
        pet_id=original.pet_id,
        registrado_por_id=usuario.id,
        estorno_de_id=original.id,
        motivo_estorno=dados.motivo,
    )
    await gravar_com_auditoria(
        sessao, estorno, usuario=usuario, entidade="gasto", acao="estorno", antes=original
    )
    return await _com_nomes(sessao, estorno.id)


async def listar(
    sessao: AsyncSession,
    pagina: int,
    tamanho_pagina: int,
    categoria: CategoriaGasto | None,
    pet_id: int | None,
) -> tuple[list[Gasto], int]:
    return await repo_gasto.listar(sessao, pagina, tamanho_pagina, categoria, pet_id)


async def _com_nomes(sessao: AsyncSession, gasto_id: int) -> Gasto:
    gasto = await repo_gasto.obter(sessao, gasto_id)
    assert gasto is not None  # acabou de ser gravado nesta sessao
    return gasto
