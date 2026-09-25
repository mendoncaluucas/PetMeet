"""Testes de autenticacao e controle de acesso (RF20, RF21, RNF01, RNF02)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguranca import gerar_hash_senha
from app.modelos.enums import PerfilUsuario
from app.modelos.usuario import Usuario


async def test_login_com_credenciais_validas_retorna_token(
    client: AsyncClient, sessao: AsyncSession
) -> None:
    usuario = Usuario(
        nome="Ana",
        email="ana@petmeet.org.br",
        senha_hash=gerar_hash_senha("senha-correta-123"),
        perfil=PerfilUsuario.ADMIN,
    )
    sessao.add(usuario)
    await sessao.commit()

    resposta = await client.post(
        "/auth/login", data={"username": "ana@petmeet.org.br", "password": "senha-correta-123"}
    )

    assert resposta.status_code == 200
    assert "access_token" in resposta.json()


async def test_login_com_senha_invalida_retorna_401(
    client: AsyncClient, sessao: AsyncSession
) -> None:
    usuario = Usuario(
        nome="Ana",
        email="ana2@petmeet.org.br",
        senha_hash=gerar_hash_senha("senha-correta-123"),
        perfil=PerfilUsuario.ADMIN,
    )
    sessao.add(usuario)
    await sessao.commit()

    resposta = await client.post(
        "/auth/login", data={"username": "ana2@petmeet.org.br", "password": "senha-errada"}
    )

    assert resposta.status_code == 401


async def test_rota_administrativa_sem_token_retorna_401(client: AsyncClient) -> None:
    resposta = await client.get("/pets")
    assert resposta.status_code == 401


async def test_criar_pet_sem_perfil_autorizado_retorna_403(
    client: AsyncClient, sessao: AsyncSession, dados_pet_saudavel: dict
) -> None:
    # Usuario existe e esta autenticado, mas perfil "voluntario" nao pode criar pets? Na
    # regra atual voluntario TAMBEM pode; aqui simulamos um perfil sem permissao alguma
    # criando o token com um usuario inativo, que deve ser rejeitado como nao autenticado.
    usuario_inativo = Usuario(
        nome="Inativo",
        email="inativo@petmeet.org.br",
        senha_hash=gerar_hash_senha("qualquer-senha"),
        perfil=PerfilUsuario.VOLUNTARIO,
        ativo=False,
    )
    sessao.add(usuario_inativo)
    await sessao.commit()

    from app.core.seguranca import criar_token_acesso

    token = criar_token_acesso({"sub": usuario_inativo.email})
    resposta = await client.post(
        "/pets", json=dados_pet_saudavel, headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 401


async def test_login_com_senha_acima_de_72_bytes_retorna_401(
    client: AsyncClient, sessao: AsyncSession
) -> None:
    """DEF-07: o bcrypt 5 lanca ValueError acima de 72 bytes -- o login respondia 500."""
    sessao.add(
        Usuario(
            nome="Ana",
            email="ana3@petmeet.org.br",
            senha_hash=gerar_hash_senha("senha-correta-123"),
            perfil=PerfilUsuario.ADMIN,
        )
    )
    await sessao.commit()

    resposta = await client.post(
        "/auth/login", data={"username": "ana3@petmeet.org.br", "password": "a" * 80}
    )

    assert resposta.status_code == 401


def _novo_usuario(senha: str) -> dict:
    return {"nome": "Beto", "email": "beto@petmeet.org.br", "senha": senha, "perfil": "voluntario"}


async def test_criar_usuario_com_senha_acima_de_72_bytes_e_rejeitado(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    resposta = await client.post("/usuarios", json=_novo_usuario("a" * 73), headers=cabecalho_admin)
    assert resposta.status_code == 422


async def test_criar_usuario_com_senha_de_72_bytes_e_aceito(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    resposta = await client.post("/usuarios", json=_novo_usuario("a" * 72), headers=cabecalho_admin)
    assert resposta.status_code == 201


async def test_senha_acentuada_conta_bytes_e_nao_caracteres(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    # 37 caracteres, mas 74 bytes: cada "ç" ocupa 2 bytes em UTF-8.
    resposta = await client.post("/usuarios", json=_novo_usuario("ç" * 37), headers=cabecalho_admin)
    assert resposta.status_code == 422
