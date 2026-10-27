"""Hash de senha (bcrypt) e emissao/validacao de token JWT (RNF01, RF20)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import obter_configuracoes

configuracoes = obter_configuracoes()

# O bcrypt so aceita ate 72 bytes de senha -- e a partir da versao 5.0 lanca ValueError
# acima disso, em vez de truncar. O limite e em bytes: letras acentuadas ocupam 2.
LIMITE_BYTES_SENHA = 72


def senha_cabe_no_bcrypt(senha: str) -> bool:
    return len(senha.encode("utf-8")) <= LIMITE_BYTES_SENHA


def gerar_hash_senha(senha: str) -> str:
    """Gera o hash bcrypt da senha em texto puro. Nunca armazenar a senha original."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    # Nenhum hash guardado veio de senha acima do limite (o cadastro recusa), entao
    # uma senha assim nunca confere -- e responder False evita o ValueError do bcrypt.
    if not senha_cabe_no_bcrypt(senha):
        return False
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_token_acesso(dados: dict[str, Any]) -> str:
    """Cria um JWT de acesso contendo o payload informado (tipicamente {'sub': email})."""
    expira_em = datetime.now(UTC) + timedelta(minutes=configuracoes.TOKEN_EXPIRACAO_MINUTOS)
    payload = {**dados, "exp": expira_em}
    return jwt.encode(payload, configuracoes.SECRET_KEY, algorithm=configuracoes.ALGORITMO_JWT)


def decodificar_token_acesso(token: str) -> dict[str, Any] | None:
    """Retorna o payload do token se valido, ou None se invalido/expirado."""
    try:
        return jwt.decode(token, configuracoes.SECRET_KEY, algorithms=[configuracoes.ALGORITMO_JWT])
    except JWTError:
        return None
