"""Popula o banco com dados minimos para comecar a usar a API.

Uso:
    python -m scripts.seed
"""

import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguranca import gerar_hash_senha
from app.db.sessao import FabricaSessao
from app.modelos.enums import EspeciePet, PerfilUsuario, StatusSaudePet
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.repositorios import usuario as repo_usuario


async def popular(sessao: AsyncSession) -> None:
    if await repo_usuario.obter_por_email(sessao, "admin@petmeet.org.br") is None:
        admin = Usuario(
            nome="Administrador PetMeet",
            email="admin@petmeet.org.br",
            senha_hash=gerar_hash_senha("admin123456"),
            perfil=PerfilUsuario.ADMIN,
        )
        sessao.add(admin)
        print("Usuario admin criado: admin@petmeet.org.br / admin123456")

    sessao.add_all(
        [
            Pet(
                nome="Rex",
                especie=EspeciePet.CACHORRO,
                idade=3,
                data_resgate=date(2025, 1, 10),
                status_saude=StatusSaudePet.SAUDAVEL,
            ),
            Pet(
                nome="Mingau",
                especie=EspeciePet.GATO,
                idade=1,
                data_resgate=date(2025, 3, 22),
                status_saude=StatusSaudePet.EM_TRATAMENTO_MEDICO,
                doenca_atual="Verminose",
            ),
        ]
    )
    await sessao.commit()
    print("Pets de exemplo cadastrados.")


async def main() -> None:
    async with FabricaSessao() as sessao:
        await popular(sessao)


if __name__ == "__main__":
    asyncio.run(main())
