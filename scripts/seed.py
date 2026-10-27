"""Popula o banco com dados minimos para comecar a usar a API.

Pode rodar quantas vezes for preciso: so cria o que ainda nao existe.

Uso:
    python -m scripts.seed
"""

import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguranca import gerar_hash_senha
from app.db.sessao import FabricaSessao
from app.modelos.enums import EspeciePet, PerfilUsuario, StatusSaudePet
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.repositorios import usuario as repo_usuario

_PETS_DE_EXEMPLO = (
    {
        "nome": "Rex",
        "especie": EspeciePet.CACHORRO,
        "idade": 3,
        "data_resgate": date(2025, 1, 10),
        "status_saude": StatusSaudePet.SAUDAVEL,
    },
    {
        "nome": "Mingau",
        "especie": EspeciePet.GATO,
        "idade": 1,
        "data_resgate": date(2025, 3, 22),
        "status_saude": StatusSaudePet.EM_TRATAMENTO_MEDICO,
        "doenca_atual": "Verminose",
    },
)


_USUARIOS_DE_EXEMPLO = (
    ("Administrador PetMeet", "admin@petmeet.org.br", "admin123456", PerfilUsuario.ADMIN),
    ("Veterinaria PetMeet", "veterinario@petmeet.org.br", "vet123456", PerfilUsuario.VETERINARIO),
)


async def popular(sessao: AsyncSession) -> None:
    for nome, email, senha, perfil in _USUARIOS_DE_EXEMPLO:
        await _garantir_usuario(sessao, nome, email, senha, perfil)
    await _garantir_pets_de_exemplo(sessao)
    await sessao.commit()


async def _garantir_usuario(
    sessao: AsyncSession, nome: str, email: str, senha: str, perfil: PerfilUsuario
) -> None:
    if await repo_usuario.obter_por_email(sessao, email) is not None:
        return
    sessao.add(Usuario(nome=nome, email=email, senha_hash=gerar_hash_senha(senha), perfil=perfil))
    print(f"Usuario {perfil.value} criado: {email} / {senha}")


async def _garantir_pets_de_exemplo(sessao: AsyncSession) -> None:
    # Pet nao tem chave natural; o nome basta para reconhecer os dados de exemplo.
    nomes = [dados["nome"] for dados in _PETS_DE_EXEMPLO]
    existentes = set(await sessao.scalars(select(Pet.nome).where(Pet.nome.in_(nomes))))
    novos = [Pet(**dados) for dados in _PETS_DE_EXEMPLO if dados["nome"] not in existentes]
    sessao.add_all(novos)
    print(f"Pets de exemplo: {len(novos)} cadastrados, {len(existentes)} ja existiam.")


async def main() -> None:
    async with FabricaSessao() as sessao:
        await popular(sessao)


if __name__ == "__main__":
    asyncio.run(main())
