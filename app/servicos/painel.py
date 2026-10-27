"""Resumo do Painel (DEF-09, DEF-10).

O Painel baixava as primeiras 100 linhas de cada listagem e calculava no navegador:
passando de 100 registros, as contagens ficavam erradas, e "esperando ha mais tempo"
ignorava justamente os pets mais antigos. O mes era o de UTC.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import intervalo_do_mes
from app.esquemas.painel import PetResumido, ProcessoResumido, ResumoPainel
from app.repositorios import painel as repo_painel

# As listas sao para bater o olho; as telas de Pets e Adocoes mostram tudo.
_TAMANHO_DAS_LISTAS = 20
_TAMANHO_DA_FILA_DE_ESPERA = 5


async def montar_resumo(sessao: AsyncSession, hoje: date) -> ResumoPainel:
    pets_total, pets_disponiveis, pets_em_tratamento = await repo_painel.contar_pets(sessao)
    em_andamento, aguardando = await repo_painel.contar_processos_ativos(sessao)
    inicio, fim = intervalo_do_mes(hoje)
    doacoes_total, doacoes_quantidade = await repo_painel.somar_doacoes(sessao, inicio, fim)

    return ResumoPainel(
        pets_total=pets_total,
        pets_disponiveis=pets_disponiveis,
        pets_em_tratamento=pets_em_tratamento,
        processos_em_andamento=em_andamento,
        processos_aguardando_finalizacao=aguardando,
        mes_de_referencia=inicio.strftime("%Y-%m"),
        doacoes_do_mes_total=doacoes_total,
        doacoes_do_mes_quantidade=doacoes_quantidade,
        em_tratamento=[
            PetResumido.model_validate(pet)
            for pet in await repo_painel.pets_em_tratamento(sessao, _TAMANHO_DAS_LISTAS)
        ],
        em_andamento=[
            ProcessoResumido.model_validate(linha._mapping)
            for linha in await repo_painel.processos_em_andamento(sessao, _TAMANHO_DAS_LISTAS)
        ],
        esperando_ha_mais_tempo=[
            PetResumido.model_validate(pet)
            for pet in await repo_painel.pets_esperando_ha_mais_tempo(
                sessao, _TAMANHO_DA_FILA_DE_ESPERA
            )
        ],
    )
