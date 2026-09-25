"""Testes da regra critica do sistema (RN01/RF16) e da concorrencia (RN02/RF17/RNF18).

Este arquivo cobre exatamente o requisito central do enunciado: 'um pet com
status Em Tratamento Medico nao pode ter seu processo de adocao finalizado'
(ressalvada a excecao da RN01), alem da garantia de que dois processos do
mesmo pet nunca finalizam ao mesmo tempo.
"""

import asyncio
from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RegraNegocioError
from app.esquemas.processo_adocao import ProcessoAdocaoAtualizarStatus
from app.modelos.adotante import Adotante
from app.modelos.enums import SituacaoAdocaoPet, StatusProcessoAdocao
from app.modelos.pet import Pet
from app.modelos.processo_adocao import ProcessoAdocao
from app.servicos import processo_adocao as servico_processo
from testes.conftest import FabricaSessaoTeste, esperar_conexoes_bloqueadas


async def _criar_pet(sessao: AsyncSession, **sobrescritas) -> Pet:
    dados = {
        "nome": "Pet de Teste",
        "especie": "cachorro",
        "idade": 4,
        "data_resgate": date(2025, 1, 1),
        "status_saude": "saudavel",
        "situacao_adocao": "disponivel",
    }
    dados.update(sobrescritas)  # permite sobrescrever qualquer valor padrao
    pet = Pet(**dados)
    sessao.add(pet)
    await sessao.commit()
    await sessao.refresh(pet)
    return pet


async def _criar_adotante(sessao: AsyncSession, cpf: str) -> Adotante:
    adotante = Adotante(
        nome="Adotante de Teste",
        cpf=cpf,
        email=f"{cpf}@teste.com",
        telefone="11999999999",
        endereco="Rua Teste, 123",
    )
    sessao.add(adotante)
    await sessao.commit()
    await sessao.refresh(adotante)
    return adotante


async def test_criar_processo_marca_pet_como_em_processo_adocao(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    pet = await _criar_pet(sessao)
    adotante = await _criar_adotante(sessao, "11111111111")

    resposta = await client.post(
        "/processos-adocao",
        json={"pet_id": pet.id, "adotante_id": adotante.id},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 201
    await sessao.refresh(pet)
    assert pet.situacao_adocao.value == "em_processo_adocao"


async def test_criar_segundo_processo_para_pet_ja_em_processo_e_rejeitado(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    # RF17 (parte 1): nao pode haver dois processos concorrentes para o mesmo pet.
    pet = await _criar_pet(sessao)
    adotante1 = await _criar_adotante(sessao, "22222222222")
    adotante2 = await _criar_adotante(sessao, "33333333333")

    await client.post(
        "/processos-adocao",
        json={"pet_id": pet.id, "adotante_id": adotante1.id},
        headers=cabecalho_admin,
    )
    resposta = await client.post(
        "/processos-adocao",
        json={"pet_id": pet.id, "adotante_id": adotante2.id},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 422


async def test_criar_processo_para_pet_ja_adotado_e_rejeitado(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    # RN04.
    pet = await _criar_pet(sessao, situacao_adocao="adotado")
    adotante = await _criar_adotante(sessao, "44444444444")

    resposta = await client.post(
        "/processos-adocao",
        json={"pet_id": pet.id, "adotante_id": adotante.id},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 422


async def test_finalizar_processo_pet_saudavel_funciona(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    pet = await _criar_pet(sessao)
    adotante = await _criar_adotante(sessao, "55555555555")
    processo = (
        await client.post(
            "/processos-adocao",
            json={"pet_id": pet.id, "adotante_id": adotante.id},
            headers=cabecalho_admin,
        )
    ).json()

    resposta = await client.patch(
        f"/processos-adocao/{processo['id']}/status",
        json={"status": "finalizado"},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "finalizado"
    await sessao.refresh(pet)
    assert pet.situacao_adocao.value == "adotado"


async def test_finalizar_processo_pet_em_tratamento_sem_acompanhamento_e_rejeitado(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    # RN01/RF16: a regra critica do enunciado.
    pet = await _criar_pet(sessao, status_saude="em_tratamento_medico", doenca_atual="Cinomose")
    adotante = await _criar_adotante(sessao, "66666666666")
    processo = (
        await client.post(
            "/processos-adocao",
            json={"pet_id": pet.id, "adotante_id": adotante.id},
            headers=cabecalho_admin,
        )
    ).json()

    resposta = await client.patch(
        f"/processos-adocao/{processo['id']}/status",
        json={"status": "finalizado", "acompanhamento_medico_em_dia": False},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 422
    await sessao.refresh(pet)
    assert pet.situacao_adocao.value == "em_processo_adocao"


async def test_finalizar_processo_pet_em_tratamento_com_acompanhamento_em_dia_funciona(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    # RN01: excecao expressa -- finaliza se o adotante estiver de acordo com o acompanhamento.
    pet = await _criar_pet(sessao, status_saude="em_tratamento_medico", doenca_atual="Cinomose")
    adotante = await _criar_adotante(sessao, "77777777777")
    processo = (
        await client.post(
            "/processos-adocao",
            json={"pet_id": pet.id, "adotante_id": adotante.id},
            headers=cabecalho_admin,
        )
    ).json()

    resposta = await client.patch(
        f"/processos-adocao/{processo['id']}/status",
        json={"status": "finalizado", "acompanhamento_medico_em_dia": True},
        headers=cabecalho_admin,
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "finalizado"


async def test_finalizacao_concorrente_do_mesmo_pet_apenas_uma_vence(sessao: AsyncSession) -> None:
    """RN02/RF17/RNF18: dois processos do MESMO pet tentando finalizar ao mesmo tempo --
    apenas um pode vencer. Usa duas sessoes/conexoes reais (nao o mesmo objeto de sessao)
    para reproduzir concorrencia de banco de verdade, e chama a camada de servico
    diretamente (sem HTTP) para isolar exatamente a garantia que queremos testar.
    """
    pet = await _criar_pet(sessao)
    adotante1 = await _criar_adotante(sessao, "88888888881")
    adotante2 = await _criar_adotante(sessao, "88888888882")

    # Cenario artificial: dois processos abertos para o mesmo pet, simulando uma falha
    # anterior na camada de aplicacao -- a garantia final precisa vir do banco.
    processo1 = ProcessoAdocao(
        pet_id=pet.id, adotante_id=adotante1.id, status=StatusProcessoAdocao.EM_ANALISE
    )
    processo2 = ProcessoAdocao(
        pet_id=pet.id, adotante_id=adotante2.id, status=StatusProcessoAdocao.EM_ANALISE
    )
    sessao.add_all([processo1, processo2])
    await sessao.commit()
    id_processo1, id_processo2 = processo1.id, processo2.id

    async def _finalizar(processo_id: int) -> str:
        async with FabricaSessaoTeste() as sessao_local:
            try:
                await servico_processo.atualizar_status_processo(
                    sessao_local,
                    processo_id,
                    ProcessoAdocaoAtualizarStatus(status=StatusProcessoAdocao.FINALIZADO),
                )
                return "sucesso"
            except (RegraNegocioError, ConflitoError):
                return "rejeitado"

    resultados = await asyncio.gather(_finalizar(id_processo1), _finalizar(id_processo2))

    assert sorted(resultados) == ["rejeitado", "sucesso"]


async def test_cancelar_e_finalizar_o_mesmo_processo_ao_mesmo_tempo_apenas_um_vence(
    sessao: AsyncSession,
) -> None:
    """DEF-06: cancelar e finalizar o MESMO processo ao mesmo tempo -- so um pode vencer.

    Em sequencia, a segunda mudanca e recusada porque o processo ja esta encerrado.
    Para reproduzir a corrida de forma deterministica, uma terceira conexao segura a
    trava do pet enquanto as duas requisicoes leem o processo; so depois de as duas
    estarem paradas na trava ela e liberada.
    """
    pet = await _criar_pet(sessao, situacao_adocao="em_processo_adocao")
    adotante = await _criar_adotante(sessao, "99999999991")
    processo = ProcessoAdocao(
        pet_id=pet.id, adotante_id=adotante.id, status=StatusProcessoAdocao.EM_ANALISE
    )
    sessao.add(processo)
    await sessao.commit()

    async def _mudar_status(novo: StatusProcessoAdocao) -> str:
        async with FabricaSessaoTeste() as sessao_local:
            try:
                await servico_processo.atualizar_status_processo(
                    sessao_local, processo.id, ProcessoAdocaoAtualizarStatus(status=novo)
                )
                return "sucesso"
            except (RegraNegocioError, ConflitoError):
                return "rejeitado"

    async with FabricaSessaoTeste() as trava:
        await trava.execute(select(Pet).where(Pet.id == pet.id).with_for_update())
        tarefas = [
            asyncio.create_task(_mudar_status(StatusProcessoAdocao.CANCELADO)),
            asyncio.create_task(_mudar_status(StatusProcessoAdocao.FINALIZADO)),
        ]
        await esperar_conexoes_bloqueadas(2)
        await trava.rollback()
    resultados = await asyncio.gather(*tarefas)

    assert sorted(resultados) == ["rejeitado", "sucesso"]

    async with FabricaSessaoTeste() as leitura:
        final = await leitura.get(ProcessoAdocao, processo.id)
        pet_final = await leitura.get(Pet, pet.id)
    esperado = {
        StatusProcessoAdocao.CANCELADO: SituacaoAdocaoPet.DISPONIVEL,
        StatusProcessoAdocao.FINALIZADO: SituacaoAdocaoPet.ADOTADO,
    }
    assert pet_final.situacao_adocao == esperado[final.status]
