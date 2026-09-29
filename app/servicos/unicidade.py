"""Tratamento comum de cadastro duplicado (DEF-08)."""

from collections.abc import Awaitable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RegraNegocioError

T = TypeVar("T")

_VIOLACAO_DE_UNICIDADE = "23505"  # SQLSTATE do Postgres


async def gravar_sem_duplicar(sessao: AsyncSession, gravacao: Awaitable[T], mensagem: str) -> T:
    """Executa a gravacao e responde a violacao de unicidade como a consulta previa responde.

    Os servicos consultam antes de gravar, para dar uma mensagem clara. Mas duas
    requisicoes iguais ao mesmo tempo passam juntas pela consulta e o indice unico barra
    a segunda -- que recebia 500. Aqui ela recebe o que receberia em sequencia.

    So a unicidade e traduzida. Outra violacao -- uma chave externa para um registro que
    acabou de ser excluido, por exemplo -- nao e "ja existe" e segue adiante como erro.
    """
    try:
        return await gravacao
    except IntegrityError as erro:
        if getattr(erro.orig, "sqlstate", None) != _VIOLACAO_DE_UNICIDADE:
            raise
        await sessao.rollback()
        raise RegraNegocioError(mensagem) from erro
