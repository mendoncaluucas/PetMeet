"""Regras de negocio de Usuario (RF20, RF21)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RegraNegocioError
from app.core.seguranca import gerar_hash_senha
from app.esquemas.usuario import UsuarioCriar
from app.modelos.usuario import Usuario
from app.repositorios import usuario as repo_usuario
from app.servicos.unicidade import gravar_sem_duplicar


async def criar_usuario(sessao: AsyncSession, dados: UsuarioCriar) -> Usuario:
    duplicado = f"Ja existe um usuario cadastrado com o email {dados.email}."
    if await repo_usuario.obter_por_email(sessao, dados.email) is not None:
        raise RegraNegocioError(duplicado)

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        perfil=dados.perfil,
    )
    return await gravar_sem_duplicar(sessao, repo_usuario.criar(sessao, usuario), duplicado)
