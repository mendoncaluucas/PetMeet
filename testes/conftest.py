"""Fixtures compartilhadas pela suite de testes (RNF10, RNF13).

Usa um banco PostgreSQL real e isolado (DATABASE_URL_TESTE) em vez de mocks -- as
regras criticas do PetMeet (RN01, RN02, RNF18) dependem de constraints e locks
reais do banco, que um mock nao reproduziria com fidelidade.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import obter_configuracoes
from app.core.seguranca import criar_token_acesso, gerar_hash_senha
from app.db.base import Base
from app.db.sessao import obter_sessao
from app.main import app
from app.modelos.enums import PerfilUsuario
from app.modelos.usuario import Usuario

configuracoes = obter_configuracoes()

engine_teste = create_async_engine(configuracoes.DATABASE_URL_TESTE)
FabricaSessaoTeste = async_sessionmaker(bind=engine_teste, expire_on_commit=False)


async def esperar_conexoes_bloqueadas(quantidade: int) -> None:
    """Espera ate `quantidade` conexoes estarem paradas esperando uma trava do banco.

    Usado para reproduzir corridas de forma deterministica. Consulta numa sessao nova a
    cada volta: dentro de uma mesma transacao o pg_stat_activity devolve sempre o mesmo
    retrato.
    """
    bloqueadas = 0
    for _ in range(100):
        async with FabricaSessaoTeste() as consulta:
            bloqueadas = await consulta.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE wait_event_type = 'Lock' AND datname = current_database()"
                )
            )
        if bloqueadas >= quantidade:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"esperava {quantidade} conexoes bloqueadas, vieram {bloqueadas}")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def preparar_banco() -> AsyncGenerator[None, None]:
    async with engine_teste.begin() as conexao:
        await conexao.run_sync(Base.metadata.create_all)
    yield
    async with engine_teste.begin() as conexao:
        await conexao.run_sync(Base.metadata.drop_all)
    await engine_teste.dispose()


@pytest_asyncio.fixture(autouse=True)
async def limpar_tabelas() -> AsyncGenerator[None, None]:
    """Isola os testes: trunca todas as tabelas antes de cada teste.

    Necessario porque os servicos fazem commit proprio (ex.: finalizar um
    processo de adocao) -- um simples rollback ao final do teste nao desfaria
    esses commits.
    """
    yield
    async with engine_teste.begin() as conexao:
        for tabela in reversed(Base.metadata.sorted_tables):
            await conexao.execute(tabela.delete())


@pytest_asyncio.fixture
async def sessao() -> AsyncGenerator[AsyncSession, None]:
    async with FabricaSessaoTeste() as sessao_teste:
        yield sessao_teste


@pytest_asyncio.fixture
async def client(sessao: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _obter_sessao_teste() -> AsyncGenerator[AsyncSession, None]:
        yield sessao

    app.dependency_overrides[obter_sessao] = _obter_sessao_teste
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://testserver") as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


async def _criar_usuario(sessao: AsyncSession, perfil: PerfilUsuario, email: str) -> Usuario:
    usuario = Usuario(
        nome="Usuario de Teste",
        email=email,
        senha_hash=gerar_hash_senha("senha-super-segura"),
        perfil=perfil,
    )
    sessao.add(usuario)
    await sessao.commit()
    await sessao.refresh(usuario)
    return usuario


@pytest_asyncio.fixture
async def cabecalho_admin(sessao: AsyncSession) -> dict[str, str]:
    usuario = await _criar_usuario(sessao, PerfilUsuario.ADMIN, "admin@petmeet.org.br")
    token = criar_token_acesso({"sub": usuario.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def dados_pet_saudavel() -> dict:
    return {
        "nome": "Rex",
        "especie": "cachorro",
        "idade": 3,
        "data_resgate": "2025-01-10",
        "status_saude": "saudavel",
    }
