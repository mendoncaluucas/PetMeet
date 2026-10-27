"""O que gasto e doacao tem em comum ao registrar e estornar (fase 3, H9, D13)."""

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RegraNegocioError
from app.esquemas.gasto import LancamentoAuditado
from app.modelos.usuario import Usuario
from app.servicos import auditoria as servico_auditoria
from app.servicos.unicidade import gravar_sem_duplicar

JA_ESTORNADO = "Este lancamento ja foi estornado."


class Lancamento(Protocol):
    id: int
    estorno_de_id: int | None


def conferir_estornavel(original: Lancamento, ja_tem_estorno: bool) -> None:
    if original.estorno_de_id is not None:
        raise RegraNegocioError("Um estorno nao se estorna.")
    if ja_tem_estorno:
        raise RegraNegocioError(JA_ESTORNADO)


async def gravar_com_auditoria(
    sessao: AsyncSession,
    lancamento: Lancamento,
    *,
    usuario: Usuario,
    entidade: str,
    acao: str,
    antes: Lancamento | None = None,
) -> None:
    """Grava o lancamento e a linha de auditoria na mesma transacao (H9.7).

    O flush vem antes para o lancamento ganhar id. Um segundo estorno simultaneo do mesmo
    original esbarra no UNIQUE de estorno_de_id aqui e recebe a mesma recusa do sequencial.
    """
    sessao.add(lancamento)
    await gravar_sem_duplicar(sessao, sessao.flush(), JA_ESTORNADO)
    servico_auditoria.registrar(
        sessao,
        usuario_id=usuario.id,
        entidade=entidade,
        entidade_id=lancamento.id,
        acao=acao,
        antes=LancamentoAuditado.model_validate(antes, from_attributes=True) if antes else None,
        depois=LancamentoAuditado.model_validate(lancamento, from_attributes=True),
    )
    await sessao.commit()
