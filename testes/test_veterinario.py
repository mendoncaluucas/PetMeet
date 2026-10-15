"""Fase 2, H1 e H2: perfil veterinario e alta medica so pelo veterinario.

Criterios em docs/HISTORIAS-FASE-2.md.
"""

import asyncio
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import NaoAutorizadoError
from app.esquemas.pet import PetAtualizarStatusSaude
from app.main import app
from app.modelos.enums import EspeciePet, PerfilUsuario, StatusSaudePet
from app.modelos.log_auditoria import LogAuditoria
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.servicos import pet as servico_pet
from testes.conftest import FabricaSessaoTeste, cabecalho_do_perfil, esperar_conexoes_bloqueadas

# O que o veterinario pode usar (matriz da secao 2). Qualquer outra rota protegida,
# inclusive as que forem criadas depois, tem de responder 403 para ele.
_ROTAS_DO_VETERINARIO = {
    ("GET", "/auth/me"),
    ("GET", "/pets"),
    ("GET", "/pets/{pet_id}"),
    ("PATCH", "/pets/{pet_id}/status-saude"),
    ("GET", "/pets/{pet_id}/atendimentos"),
    ("POST", "/pets/{pet_id}/atendimentos"),
    ("POST", "/atendimentos/{atendimento_id}/anulacao"),
    ("GET", "/vacinas"),
    ("POST", "/vacinas"),
    ("PATCH", "/vacinas/{vacina_id}"),
    ("GET", "/pets/{pet_id}/cartao-vacinacao"),
    ("POST", "/pets/{pet_id}/aplicacoes-vacina"),
    ("POST", "/aplicacoes-vacina/{aplicacao_id}/anulacao"),
    ("GET", "/vacinacao/alertas"),
    ("GET", "/pets/{pet_id}/padrinhos"),  # so a contagem, sem nomes (H7.6)
}


def _rotas_protegidas() -> list[tuple[str, str]]:
    return [
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        for metodo, operacao in operacoes.items()
        if operacao.get("security")
    ]


def _com_id(caminho: str) -> str:
    # Qualquer id serve: a permissao e conferida antes de procurar o registro.
    partes = [("1" if parte.startswith("{") else parte) for parte in caminho.split("/")]
    return "/".join(partes)


async def _criar_pet(
    sessao: AsyncSession,
    status_saude: StatusSaudePet = StatusSaudePet.SAUDAVEL,
    doenca_atual: str | None = None,
) -> Pet:
    pet = Pet(
        nome="Mingau",
        especie=EspeciePet.GATO,
        idade=1,
        data_resgate=date(2025, 3, 22),
        status_saude=status_saude,
        doenca_atual=doenca_atual,
    )
    sessao.add(pet)
    await sessao.commit()
    await sessao.refresh(pet)
    return pet


_EQUIPE = [PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO]


async def _auditoria_do_pet(sessao: AsyncSession, pet_id: int) -> list[LogAuditoria]:
    consulta = (
        select(LogAuditoria)
        .where(LogAuditoria.entidade == "pet", LogAuditoria.entidade_id == pet_id)
        .order_by(LogAuditoria.id)
    )
    return list((await sessao.scalars(consulta)).all())


# ------------------------------------------------------------------ H1: perfil


async def test_admin_cadastra_veterinario_que_entra_com_o_proprio_perfil(
    client: AsyncClient, cabecalho_admin: dict
) -> None:
    resposta = await client.post(
        "/usuarios",
        json={
            "nome": "Dra. Paula",
            "email": "paula@petmeet.org.br",
            "senha": "senha-da-paula",
            "perfil": "veterinario",
        },
        headers=cabecalho_admin,
    )
    assert resposta.status_code == 201

    login = await client.post(
        "/auth/login", data={"username": "paula@petmeet.org.br", "password": "senha-da-paula"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    eu = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert eu.json()["perfil"] == "veterinario"


def test_a_matriz_so_cita_rotas_que_existem() -> None:
    """Se uma rota da matriz for renomeada, o teste de baixo deixaria de cobri-la."""
    assert _ROTAS_DO_VETERINARIO <= set(_rotas_protegidas())


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [rota for rota in _rotas_protegidas() if rota not in _ROTAS_DO_VETERINARIO],
)
async def test_veterinario_recebe_403_fora_da_matriz(
    client: AsyncClient, cabecalho_veterinario: dict, metodo: str, caminho: str
) -> None:
    resposta = await client.request(
        metodo, _com_id(caminho), json={}, headers=cabecalho_veterinario
    )
    assert resposta.status_code == 403, resposta.text


async def test_veterinario_consulta_os_pets(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)

    lista = await client.get("/pets", headers=cabecalho_veterinario)
    ficha = await client.get(f"/pets/{pet.id}", headers=cabecalho_veterinario)

    assert lista.status_code == 200
    assert lista.json()["total"] == 1
    assert ficha.status_code == 200


# ---------------------------------------------------------- H2: alta medica


@pytest.mark.parametrize("perfil", _EQUIPE)
async def test_equipe_coloca_pet_em_tratamento(
    client: AsyncClient, sessao: AsyncSession, perfil: PerfilUsuario
) -> None:
    pet = await _criar_pet(sessao)

    resposta = await client.patch(
        f"/pets/{pet.id}/status-saude",
        json={"status_saude": "em_tratamento_medico", "doenca_atual": "Cinomose"},
        headers=await cabecalho_do_perfil(sessao, perfil),
    )

    assert resposta.status_code == 200
    assert resposta.json()["status_saude"] == "em_tratamento_medico"


@pytest.mark.parametrize("perfil", _EQUIPE)
@pytest.mark.parametrize("destino", ["saudavel", "em_recuperacao"])
async def test_equipe_nao_da_alta_de_tratamento(
    client: AsyncClient,
    sessao: AsyncSession,
    perfil: PerfilUsuario,
    destino: str,
) -> None:
    pet = await _criar_pet(sessao, StatusSaudePet.EM_TRATAMENTO_MEDICO, "Cinomose")

    resposta = await client.patch(
        f"/pets/{pet.id}/status-saude",
        json={"status_saude": destino},
        headers=await cabecalho_do_perfil(sessao, perfil),
    )

    assert resposta.status_code == 403
    assert "veterinario" in resposta.json()["detalhe"]
    await sessao.refresh(pet)
    assert pet.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO
    assert pet.doenca_atual == "Cinomose"
    assert await _auditoria_do_pet(sessao, pet.id) == []


async def test_veterinario_da_alta_e_a_auditoria_guarda_antes_e_depois(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao, StatusSaudePet.EM_TRATAMENTO_MEDICO, "Cinomose")
    veterinario = await sessao.scalar(
        select(Usuario).where(Usuario.perfil == PerfilUsuario.VETERINARIO)
    )

    resposta = await client.patch(
        f"/pets/{pet.id}/status-saude",
        json={"status_saude": "em_recuperacao"},
        headers=cabecalho_veterinario,
    )

    assert resposta.status_code == 200
    assert resposta.json()["status_saude"] == "em_recuperacao"
    assert resposta.json()["doenca_atual"] is None
    [linha] = await _auditoria_do_pet(sessao, pet.id)
    assert linha.usuario_id == veterinario.id
    assert linha.acao == "status_saude"
    assert linha.dados_antigos == {
        "status_saude": "em_tratamento_medico",
        "doenca_atual": "Cinomose",
    }
    assert linha.dados_novos == {"status_saude": "em_recuperacao", "doenca_atual": None}


async def test_equipe_corrige_a_doenca_sem_tirar_do_tratamento(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _criar_pet(sessao, StatusSaudePet.EM_TRATAMENTO_MEDICO, "Cinomse")

    resposta = await client.patch(
        f"/pets/{pet.id}/status-saude",
        json={"status_saude": "em_tratamento_medico", "doenca_atual": "Cinomose"},
        headers=cabecalho_voluntario,
    )

    assert resposta.status_code == 200
    assert resposta.json()["doenca_atual"] == "Cinomose"
    [linha] = await _auditoria_do_pet(sessao, pet.id)
    assert linha.dados_antigos["doenca_atual"] == "Cinomse"


async def test_equipe_alterna_entre_saudavel_e_em_recuperacao(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _criar_pet(sessao)

    for destino in ("em_recuperacao", "saudavel"):
        resposta = await client.patch(
            f"/pets/{pet.id}/status-saude",
            json={"status_saude": destino},
            headers=cabecalho_voluntario,
        )
        assert resposta.status_code == 200
        assert resposta.json()["status_saude"] == destino

    assert len(await _auditoria_do_pet(sessao, pet.id)) == 2


async def test_pedir_o_status_que_o_pet_ja_tem_nao_grava_auditoria(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _criar_pet(sessao, StatusSaudePet.EM_TRATAMENTO_MEDICO, "Cinomose")

    resposta = await client.patch(
        f"/pets/{pet.id}/status-saude",
        json={"status_saude": "em_tratamento_medico", "doenca_atual": "Cinomose"},
        headers=cabecalho_voluntario,
    )

    assert resposta.status_code == 200
    assert await _auditoria_do_pet(sessao, pet.id) == []


async def test_alta_de_pet_inexistente_responde_404(
    client: AsyncClient, cabecalho_veterinario: dict
) -> None:
    resposta = await client.patch(
        "/pets/999/status-saude", json={"status_saude": "saudavel"}, headers=cabecalho_veterinario
    )
    assert resposta.status_code == 404


async def test_voluntario_nao_tira_do_tratamento_registrado_ao_mesmo_tempo(
    sessao: AsyncSession,
) -> None:
    """Alguem registra o tratamento enquanto um voluntario muda o pet para "em recuperacao".

    Sem a trava, o voluntario le "saudavel", passa pela regra e a gravacao dele sobrescreve
    o tratamento: o pet sairia do tratamento sem alta do veterinario.
    """
    pet = await _criar_pet(sessao)
    voluntario = Usuario(
        nome="Vera",
        email="vera@petmeet.org.br",
        senha_hash="x",
        perfil=PerfilUsuario.VOLUNTARIO,
    )
    sessao.add(voluntario)
    await sessao.commit()

    async def _voluntario_muda_status() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_pet.atualizar_status_saude(
                sessao_local,
                pet.id,
                PetAtualizarStatusSaude(status_saude=StatusSaudePet.EM_RECUPERACAO),
                voluntario,
            )

    async with FabricaSessaoTeste() as outra_pessoa:
        pet_na_outra_sessao = await outra_pessoa.get(Pet, pet.id)
        pet_na_outra_sessao.status_saude = StatusSaudePet.EM_TRATAMENTO_MEDICO
        pet_na_outra_sessao.doenca_atual = "Cinomose"
        await outra_pessoa.flush()  # grava sem commit: segura a linha do pet
        tarefa = asyncio.create_task(_voluntario_muda_status())
        await esperar_conexoes_bloqueadas(1)
        await outra_pessoa.commit()

    with pytest.raises(NaoAutorizadoError):
        await tarefa

    await sessao.refresh(pet)
    assert pet.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO
    assert pet.doenca_atual == "Cinomose"


async def test_doenca_so_com_espacos_nao_conta_como_informada(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict, dados_pet_saudavel: dict
) -> None:
    """Com "   " a equipe apagaria o diagnostico de um pet em tratamento sem tirar o status."""
    pet = await _criar_pet(sessao, StatusSaudePet.EM_TRATAMENTO_MEDICO, "Cinomose")

    correcao = await client.patch(
        f"/pets/{pet.id}/status-saude",
        json={"status_saude": "em_tratamento_medico", "doenca_atual": "   "},
        headers=cabecalho_voluntario,
    )
    cadastro = await client.post(
        "/pets",
        json={**dados_pet_saudavel, "status_saude": "em_tratamento_medico", "doenca_atual": "  "},
        headers=cabecalho_voluntario,
    )

    assert correcao.status_code == 422
    assert cadastro.status_code == 422
    await sessao.refresh(pet)
    assert pet.doenca_atual == "Cinomose"


async def test_espacos_nas_pontas_da_doenca_nao_viram_mudanca(
    client: AsyncClient, sessao: AsyncSession, cabecalho_voluntario: dict
) -> None:
    pet = await _criar_pet(sessao, StatusSaudePet.EM_TRATAMENTO_MEDICO, "Cinomose")

    resposta = await client.patch(
        f"/pets/{pet.id}/status-saude",
        json={"status_saude": "em_tratamento_medico", "doenca_atual": " Cinomose "},
        headers=cabecalho_voluntario,
    )

    assert resposta.json()["doenca_atual"] == "Cinomose"
    assert await _auditoria_do_pet(sessao, pet.id) == []
