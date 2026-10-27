"""A situacao de adocao do pet so muda pelo processo (DEF-03, DEF-04, DEF-05)."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RegraNegocioError
from app.esquemas.processo_adocao import ProcessoAdocaoAtualizarStatus, ProcessoAdocaoCriar
from app.modelos.adotante import Adotante
from app.modelos.enums import SituacaoAdocaoPet, StatusProcessoAdocao, StatusSaudePet
from app.modelos.pet import Pet
from app.modelos.processo_adocao import ProcessoAdocao
from app.repositorios import processo_adocao as repo_processo
from app.servicos import processo_adocao as servico_processo
from app.servicos.unicidade import gravar_sem_duplicar


async def _pet(sessao: AsyncSession, **campos) -> Pet:
    pet = Pet(nome="Tom", especie="gato", idade=2, data_resgate=date(2026, 8, 1), **campos)
    sessao.add(pet)
    await sessao.commit()
    await sessao.refresh(pet)
    return pet


async def _adotante(sessao: AsyncSession, cpf: str) -> Adotante:
    adotante = Adotante(
        nome="Adotante",
        cpf=cpf,
        email=f"{cpf}@teste.com",
        telefone="47999990000",
        endereco="Rua Teste, 1",
    )
    sessao.add(adotante)
    await sessao.commit()
    await sessao.refresh(adotante)
    return adotante


async def _processo(
    sessao: AsyncSession, pet: Pet, adotante: Adotante, status: StatusProcessoAdocao
) -> ProcessoAdocao:
    processo = ProcessoAdocao(pet_id=pet.id, adotante_id=adotante.id, status=status)
    sessao.add(processo)
    await sessao.commit()
    return processo


async def test_situacao_de_adocao_nao_pode_mais_ser_alterada_a_mao(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    """DEF-03: a rota marcava como adotado um pet em tratamento, sem nenhum processo."""
    pet = await _pet(
        sessao, status_saude=StatusSaudePet.EM_TRATAMENTO_MEDICO, doenca_atual="Cinomose"
    )

    resposta = await client.patch(
        f"/pets/{pet.id}/situacao-adocao",
        json={"situacao_adocao": "adotado"},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 404
    await sessao.refresh(pet)
    assert pet.situacao_adocao == SituacaoAdocaoPet.DISPONIVEL


async def test_banco_recusa_dois_processos_ativos_para_o_mesmo_pet(sessao: AsyncSession) -> None:
    """Rede de seguranca: vale mesmo gravando direto no banco, sem passar pelo servico."""
    pet = await _pet(sessao)
    await _processo(
        sessao, pet, await _adotante(sessao, "52998224725"), StatusProcessoAdocao.EM_ANALISE
    )

    with pytest.raises(IntegrityError):
        await _processo(
            sessao, pet, await _adotante(sessao, "12345678909"), StatusProcessoAdocao.APROVADO
        )
    await sessao.rollback()


async def test_processo_encerrado_nao_impede_um_novo_processo_ativo(sessao: AsyncSession) -> None:
    """Controle do indice: so processos em analise ou aprovados contam como ativos."""
    pet = await _pet(sessao)
    await _processo(
        sessao, pet, await _adotante(sessao, "52998224725"), StatusProcessoAdocao.CANCELADO
    )
    await _processo(
        sessao, pet, await _adotante(sessao, "12345678909"), StatusProcessoAdocao.EM_ANALISE
    )


async def test_novo_processo_com_outro_ainda_ativo_e_recusado(sessao: AsyncSession) -> None:
    """DEF-04: o atalho manual deixava o pet 'disponivel' com um processo ainda ativo, e
    um segundo processo era aberto. Dados assim podem ter ficado gravados."""
    pet = await _pet(sessao)
    await _processo(
        sessao, pet, await _adotante(sessao, "52998224725"), StatusProcessoAdocao.EM_ANALISE
    )
    segundo = await _adotante(sessao, "12345678909")

    with pytest.raises(RegraNegocioError):
        await servico_processo.criar_processo_adocao(
            sessao, ProcessoAdocaoCriar(pet_id=pet.id, adotante_id=segundo.id), responsavel_id=None
        )


async def test_cancelar_processo_nao_devolve_pet_ja_adotado(sessao: AsyncSession) -> None:
    """DEF-04: cancelar sempre devolvia o pet a 'disponivel', mesmo ja adotado."""
    pet = await _pet(sessao, situacao_adocao=SituacaoAdocaoPet.ADOTADO)
    sobra = await _processo(
        sessao, pet, await _adotante(sessao, "52998224725"), StatusProcessoAdocao.EM_ANALISE
    )

    await servico_processo.atualizar_status_processo(
        sessao, sobra.id, ProcessoAdocaoAtualizarStatus(status=StatusProcessoAdocao.CANCELADO)
    )

    await sessao.refresh(pet)
    assert pet.situacao_adocao == SituacaoAdocaoPet.ADOTADO


async def test_chave_externa_quebrada_nao_vira_mensagem_de_duplicado(sessao: AsyncSession) -> None:
    """O auxiliar de duplicidade so pode traduzir violacao de unicidade.

    Ele respondia qualquer erro de integridade como "ja existe". Com a exclusao de
    adotante (item 1.6), excluir o adotante enquanto um processo e aberto para ele
    daria "este pet ja possui um processo em andamento" -- reproduzido em 29/09.
    """
    pet = await _pet(sessao)
    sem_adotante = ProcessoAdocao(
        pet_id=pet.id, adotante_id=999_999, status=StatusProcessoAdocao.EM_ANALISE
    )

    with pytest.raises(IntegrityError):
        await gravar_sem_duplicar(sessao, repo_processo.criar(sessao, sem_adotante), "duplicado")
    await sessao.rollback()
