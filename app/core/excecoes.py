"""Excecoes de dominio e tratamento centralizado de erros (RNF14).

As camadas de servico levantam essas excecoes tipadas em vez de HTTPException,
mantendo a regra de negocio independente do protocolo HTTP. As rotas (ou o
handler global registrado em main.py) traduzem cada uma para uma resposta
padronizada, sem expor detalhes internos da aplicacao.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class ErroPetMeet(Exception):
    """Base para todas as excecoes de dominio da aplicacao."""

    def __init__(self, mensagem: str):
        self.mensagem = mensagem
        super().__init__(mensagem)


class RegraNegocioError(ErroPetMeet):
    """Violacao de uma regra de negocio (RN01-RN08). Vira HTTP 422."""


class RecursoNaoEncontradoError(ErroPetMeet):
    """Entidade buscada por id nao existe. Vira HTTP 404."""


class ConflitoError(ErroPetMeet):
    """Conflito de estado/concorrencia (ex.: RNF18). Vira HTTP 409."""


class NaoAutorizadoError(ErroPetMeet):
    """Usuario autenticado mas sem permissao para a acao (RN06/RF21). Vira HTTP 403."""


class CredenciaisInvalidasError(ErroPetMeet):
    """Login ou token invalidos (RF20). Vira HTTP 401."""


_MAPA_STATUS: dict[type[ErroPetMeet], int] = {
    # O nome antigo, HTTP_422_UNPROCESSABLE_ENTITY, esta deprecado no Starlette e vai sair.
    RegraNegocioError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    RecursoNaoEncontradoError: status.HTTP_404_NOT_FOUND,
    ConflitoError: status.HTTP_409_CONFLICT,
    NaoAutorizadoError: status.HTTP_403_FORBIDDEN,
    CredenciaisInvalidasError: status.HTTP_401_UNAUTHORIZED,
}


def registrar_tratamento_erros(app: FastAPI) -> None:
    """Registra o handler global: qualquer ErroPetMeet vira uma resposta JSON padronizada."""

    @app.exception_handler(ErroPetMeet)
    async def _handler_erro_petmeet(request: Request, exc: ErroPetMeet) -> JSONResponse:
        codigo = _MAPA_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=codigo, content={"detalhe": exc.mensagem})

    @app.exception_handler(Exception)
    async def _handler_erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
        # Nunca expor stacktrace/mensagem interna ao cliente; o detalhe vai para o log (RNF15).
        import logging

        logging.getLogger("petmeet").exception("Erro nao tratado em %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detalhe": "Erro interno inesperado. Tente novamente mais tarde."},
        )
