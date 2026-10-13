"""Trilha de auditoria (RF22).

A linha entra na mesma transacao da mudanca que ela descreve: ou as duas sao gravadas,
ou nenhuma. Quem chama faz o commit.
"""

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.log_auditoria import LogAuditoria


def registrar(
    sessao: AsyncSession,
    *,
    usuario_id: int,
    entidade: str,
    entidade_id: int,
    acao: str,
    antes: BaseModel | None,
    depois: BaseModel | None,
) -> None:
    # mode="json": a coluna JSON nao aceita date nem Decimal, e a gravacao falharia (A-05).
    sessao.add(
        LogAuditoria(
            usuario_id=usuario_id,
            entidade=entidade,
            entidade_id=entidade_id,
            acao=acao,
            dados_antigos=antes.model_dump(mode="json") if antes is not None else None,
            dados_novos=depois.model_dump(mode="json") if depois is not None else None,
        )
    )
