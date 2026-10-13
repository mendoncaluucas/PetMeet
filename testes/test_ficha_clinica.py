"""Fase 2, H3: ficha clinica (criterios em docs/HISTORIAS-FASE-2.md)."""

import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RegraNegocioError
from app.core.tempo import hoje_na_ong
from app.esquemas.atendimento_clinico import AtendimentoAnular, AtendimentoCriar
from app.modelos.atendimento_clinico import AtendimentoClinico
from app.modelos.enums import EspeciePet, PerfilUsuario, StatusSaudePet
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.servicos import atendimento_clinico as servico_atendimento
from testes.conftest import FabricaSessaoTeste, cabecalho_do_perfil, esperar_conexoes_bloqueadas

_ATENDIMENTO = {
    "data_atendimento": "2026-10-10",
    "anamnese": "Apatia ha dois dias, sem apetite.",
    "diagnostico": "Cinomose",
    "conduta": "Isolamento e suporte.",
}


async def _criar_pet(sessao: AsyncSession) -> Pet:
    pet = Pet(
        nome="Mingau",
        especie=EspeciePet.GATO,
        idade=1,
        data_resgate=date(2025, 3, 22),
        status_saude=StatusSaudePet.EM_TRATAMENTO_MEDICO,
        doenca_atual="Cinomose",
    )
    sessao.add(pet)
    await sessao.commit()
    await sessao.refresh(pet)
    return pet


async def _veterinario(sessao: AsyncSession) -> Usuario:
    return await sessao.scalar(select(Usuario).where(Usuario.perfil == PerfilUsuario.VETERINARIO))


async def _registrar(client: AsyncClient, pet_id: int, cabecalho: dict, **campos) -> dict:
    resposta = await client.post(
        f"/pets/{pet_id}/atendimentos", json={**_ATENDIMENTO, **campos}, headers=cabecalho
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ------------------------------------------------------------------ registrar


async def test_veterinario_registra_atendimento_assinado_por_ele(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict, cabecalho_admin: dict
) -> None:
    pet = await _criar_pet(sessao)
    veterinario = await _veterinario(sessao)
    admin = await sessao.scalar(select(Usuario).where(Usuario.perfil == PerfilUsuario.ADMIN))

    # Tentar assinar em nome de outra pessoa nao tem efeito: o autor vem do login.
    corpo = await _registrar(
        client, pet.id, cabecalho_veterinario, veterinario_id=admin.id, anulado_em="2026-10-10"
    )

    assert corpo["veterinario_id"] == veterinario.id
    assert corpo["veterinario_nome"] == veterinario.nome
    assert corpo["anamnese"] == _ATENDIMENTO["anamnese"]
    assert corpo["anulado_em"] is None


async def test_anamnese_e_obrigatoria_e_espacos_nao_contam(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)

    sem_anamnese = await client.post(
        f"/pets/{pet.id}/atendimentos",
        json={"data_atendimento": "2026-10-10"},
        headers=cabecalho_veterinario,
    )
    so_espacos = await client.post(
        f"/pets/{pet.id}/atendimentos",
        json={**_ATENDIMENTO, "anamnese": "   "},
        headers=cabecalho_veterinario,
    )

    assert sem_anamnese.status_code == 422
    assert so_espacos.status_code == 422


async def test_diagnostico_e_conduta_sao_opcionais(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)

    corpo = await _registrar(client, pet.id, cabecalho_veterinario, diagnostico="  ", conduta=None)

    assert corpo["diagnostico"] is None
    assert corpo["conduta"] is None


async def test_data_no_futuro_e_recusada(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)
    amanha = hoje_na_ong() + timedelta(days=1)

    resposta = await client.post(
        f"/pets/{pet.id}/atendimentos",
        json={**_ATENDIMENTO, "data_atendimento": amanha.isoformat()},
        headers=cabecalho_veterinario,
    )
    hoje = await client.post(
        f"/pets/{pet.id}/atendimentos",
        json={**_ATENDIMENTO, "data_atendimento": hoje_na_ong().isoformat()},
        headers=cabecalho_veterinario,
    )

    assert resposta.status_code == 422
    assert hoje.status_code == 201


async def test_hoje_e_o_dia_de_brasilia_e_nao_o_do_servidor(sessao: AsyncSession) -> None:
    """22h de 15/10 em Brasilia ja e 16/10 em UTC: o atendimento de 15/10 vale, o de 16/10 nao."""
    pet = await _criar_pet(sessao)
    veterinario = Usuario(
        nome="Dra. Paula", email="paula@x.org", senha_hash="x", perfil=PerfilUsuario.VETERINARIO
    )
    sessao.add(veterinario)
    await sessao.commit()
    hoje = hoje_na_ong(datetime(2026, 10, 16, 1, 0, tzinfo=UTC))
    assert hoje == date(2026, 10, 15)

    aceito = await servico_atendimento.registrar(
        sessao,
        pet.id,
        AtendimentoCriar(data_atendimento=date(2026, 10, 15), anamnese="Retorno"),
        veterinario,
        hoje=hoje,
    )
    assert aceito.data_atendimento == date(2026, 10, 15)

    with pytest.raises(RegraNegocioError):
        await servico_atendimento.registrar(
            sessao,
            pet.id,
            AtendimentoCriar(data_atendimento=date(2026, 10, 16), anamnese="Retorno"),
            veterinario,
            hoje=hoje,
        )


async def test_registrar_nao_muda_o_status_de_saude(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)

    await _registrar(client, pet.id, cabecalho_veterinario, diagnostico="Curado")

    await sessao.refresh(pet)
    assert pet.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO


async def test_pet_inexistente_responde_404(
    client: AsyncClient, cabecalho_veterinario: dict
) -> None:
    registrar = await client.post(
        "/pets/999/atendimentos", json=_ATENDIMENTO, headers=cabecalho_veterinario
    )
    listar = await client.get("/pets/999/atendimentos", headers=cabecalho_veterinario)

    assert registrar.status_code == 404
    assert listar.status_code == 404


# ---------------------------------------------------------------------- ficha


async def test_ficha_lista_do_mais_recente_para_o_mais_antigo(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)
    antigo = await _registrar(client, pet.id, cabecalho_veterinario, data_atendimento="2026-09-01")
    recente = await _registrar(client, pet.id, cabecalho_veterinario, data_atendimento="2026-10-10")
    mesmo_dia = await _registrar(
        client, pet.id, cabecalho_veterinario, data_atendimento="2026-10-10"
    )

    resposta = await client.get(f"/pets/{pet.id}/atendimentos", headers=cabecalho_veterinario)

    assert resposta.json()["total"] == 3
    assert [item["id"] for item in resposta.json()["itens"]] == [
        mesmo_dia["id"],
        recente["id"],
        antigo["id"],
    ]


async def test_ficha_so_mostra_os_atendimentos_do_pet(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)
    outro = await _criar_pet(sessao)
    await _registrar(client, outro.id, cabecalho_veterinario)

    resposta = await client.get(f"/pets/{pet.id}/atendimentos", headers=cabecalho_veterinario)

    assert resposta.json() == {"itens": [], "total": 0, "pagina": 1, "tamanho_pagina": 20}


@pytest.mark.parametrize("perfil", [PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO])
async def test_equipe_consulta_mas_nao_registra_nem_anula(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict, perfil: PerfilUsuario
) -> None:
    pet = await _criar_pet(sessao)
    atendimento = await _registrar(client, pet.id, cabecalho_veterinario)
    cabecalho = await cabecalho_do_perfil(sessao, perfil)

    ficha = await client.get(f"/pets/{pet.id}/atendimentos", headers=cabecalho)
    registrar = await client.post(
        f"/pets/{pet.id}/atendimentos", json=_ATENDIMENTO, headers=cabecalho
    )
    anular = await client.post(
        f"/atendimentos/{atendimento['id']}/anulacao", json={"motivo": "x"}, headers=cabecalho
    )

    assert ficha.status_code == 200
    assert ficha.json()["total"] == 1
    assert registrar.status_code == 403
    assert anular.status_code == 403


# --------------------------------------------------------------------- anular


async def test_anular_mantem_o_atendimento_na_ficha_com_motivo_e_autor(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)
    veterinario = await _veterinario(sessao)
    atendimento = await _registrar(client, pet.id, cabecalho_veterinario)

    resposta = await client.post(
        f"/atendimentos/{atendimento['id']}/anulacao",
        json={"motivo": "  Registrado no pet errado  "},
        headers=cabecalho_veterinario,
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["anulado_em"] is not None
    assert corpo["anulado_por_nome"] == veterinario.nome
    assert corpo["motivo_anulacao"] == "Registrado no pet errado"
    assert corpo["anamnese"] == _ATENDIMENTO["anamnese"]
    ficha = await client.get(f"/pets/{pet.id}/atendimentos", headers=cabecalho_veterinario)
    assert ficha.json()["itens"][0]["motivo_anulacao"] == "Registrado no pet errado"


async def test_anular_exige_motivo(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)
    atendimento = await _registrar(client, pet.id, cabecalho_veterinario)

    for corpo in ({}, {"motivo": ""}, {"motivo": "   "}):
        resposta = await client.post(
            f"/atendimentos/{atendimento['id']}/anulacao", json=corpo, headers=cabecalho_veterinario
        )
        assert resposta.status_code == 422, corpo


async def test_anular_de_novo_responde_422(
    client: AsyncClient, sessao: AsyncSession, cabecalho_veterinario: dict
) -> None:
    pet = await _criar_pet(sessao)
    atendimento = await _registrar(client, pet.id, cabecalho_veterinario)
    url = f"/atendimentos/{atendimento['id']}/anulacao"

    primeira = await client.post(url, json={"motivo": "Erro"}, headers=cabecalho_veterinario)
    segunda = await client.post(url, json={"motivo": "Outro"}, headers=cabecalho_veterinario)

    assert primeira.status_code == 200
    assert segunda.status_code == 422
    assert segunda.json()["detalhe"] == "Este atendimento ja foi anulado."


async def test_anular_atendimento_inexistente_responde_404(
    client: AsyncClient, cabecalho_veterinario: dict
) -> None:
    resposta = await client.post(
        "/atendimentos/999/anulacao", json={"motivo": "Erro"}, headers=cabecalho_veterinario
    )
    assert resposta.status_code == 404


async def test_duas_anulacoes_ao_mesmo_tempo_so_uma_passa(sessao: AsyncSession) -> None:
    """Sem a trava, as duas leem "nao anulado" e a segunda sobrescreve motivo e autor."""
    pet = await _criar_pet(sessao)
    paula = Usuario(nome="Paula", email="p@x.org", senha_hash="x", perfil=PerfilUsuario.VETERINARIO)
    rui = Usuario(nome="Rui", email="r@x.org", senha_hash="x", perfil=PerfilUsuario.VETERINARIO)
    sessao.add_all([paula, rui])
    await sessao.commit()
    atendimento = AtendimentoClinico(
        pet_id=pet.id, veterinario_id=paula.id, data_atendimento=date(2026, 10, 10), anamnese="x"
    )
    sessao.add(atendimento)
    await sessao.commit()

    async def _rui_anula() -> None:
        async with FabricaSessaoTeste() as sessao_local:
            await servico_atendimento.anular(
                sessao_local, atendimento.id, AtendimentoAnular(motivo="Duplicado"), rui
            )

    async with FabricaSessaoTeste() as sessao_paula:
        # Paula trava a linha e ainda nao gravou quando o Rui tenta.
        travado = await sessao_paula.get(AtendimentoClinico, atendimento.id, with_for_update=True)
        tarefa = asyncio.create_task(_rui_anula())
        await esperar_conexoes_bloqueadas(1)
        travado.anulado_em = datetime.now(UTC)
        travado.anulado_por_id = paula.id
        travado.motivo_anulacao = "Pet errado"
        await sessao_paula.commit()

    with pytest.raises(RegraNegocioError):
        await tarefa

    await sessao.refresh(atendimento)
    assert atendimento.motivo_anulacao == "Pet errado"
    assert atendimento.anulado_por_id == paula.id


# --------------------------------------------------------------- historico


async def test_banco_recusa_apagar_pet_com_atendimento(sessao: AsyncSession) -> None:
    """A-09: nenhum cascade leva o historico clinico junto com o pet."""
    pet = await _criar_pet(sessao)
    veterinario = Usuario(
        nome="V", email="v@x.org", senha_hash="x", perfil=PerfilUsuario.VETERINARIO
    )
    sessao.add(veterinario)
    await sessao.commit()
    sessao.add(
        AtendimentoClinico(
            pet_id=pet.id,
            veterinario_id=veterinario.id,
            data_atendimento=date(2026, 10, 10),
            anamnese="x",
        )
    )
    await sessao.commit()

    await sessao.delete(pet)
    with pytest.raises(IntegrityError):
        await sessao.commit()
    await sessao.rollback()


async def test_banco_recusa_anulacao_pela_metade(sessao: AsyncSession) -> None:
    pet = await _criar_pet(sessao)
    veterinario = Usuario(
        nome="V", email="v@x.org", senha_hash="x", perfil=PerfilUsuario.VETERINARIO
    )
    sessao.add(veterinario)
    await sessao.commit()
    sessao.add(
        AtendimentoClinico(
            pet_id=pet.id,
            veterinario_id=veterinario.id,
            data_atendimento=date(2026, 10, 10),
            anamnese="x",
            anulado_em=datetime.now(UTC),  # sem quem nem por que
        )
    )
    with pytest.raises(IntegrityError):
        await sessao.commit()
    await sessao.rollback()
