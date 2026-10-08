"""Rota de login (RF20)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencias import SessaoAsync, UsuarioAtual
from app.esquemas.auth import TokenResposta
from app.esquemas.usuario import UsuarioResposta
from app.servicos import auth as servico_auth

roteador = APIRouter(prefix="/auth", tags=["Autenticacao"])


@roteador.post("/login", response_model=TokenResposta)
async def login(
    sessao: SessaoAsync,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResposta:
    usuario = await servico_auth.autenticar(sessao, formulario.username, formulario.password)
    token = servico_auth.gerar_token_para_usuario(usuario)
    return TokenResposta(access_token=token)


@roteador.get("/me", response_model=UsuarioResposta)
async def quem_sou_eu(usuario: UsuarioAtual) -> UsuarioResposta:
    """Usuario dono do token, com o perfil lido do banco a cada chamada.

    O painel usa para mostrar so o que o perfil pode fazer. A autorizacao continua na
    API: cada rota rele o perfil no banco, entao trocar ou inativar um usuario vale na
    hora, sem esperar o token vencer.
    """
    return UsuarioResposta.model_validate(usuario)
