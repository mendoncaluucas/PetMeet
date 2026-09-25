"""Testes do script de dados de exemplo (scripts/seed.py)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from scripts.seed import popular


async def test_seed_rodado_duas_vezes_nao_duplica_dados(sessao: AsyncSession) -> None:
    """DEF-11: rodar o seed de novo duplicava os pets de exemplo."""
    await popular(sessao)
    await popular(sessao)

    assert await sessao.scalar(select(func.count()).select_from(Usuario)) == 1
    assert await sessao.scalar(select(func.count()).select_from(Pet)) == 2
