"""Parametros de rota com os limites do banco (DEF-15).

Acima do maior INTEGER do Postgres, o banco recusa a consulta e a API respondia 500. Com o
limite declarado aqui, a requisicao para na validacao e responde 422. Todo id que chega pelo
caminho ou pela consulta usa estes tipos; o teste de contrato (testes/test_limites.py) falha
se uma rota nova receber um numero sem limite.
"""

from typing import Annotated

from fastapi import Path, Query

from app.esquemas.comuns import MAIOR_INTEIRO_DO_BANCO

IdNoCaminho = Annotated[int, Path(le=MAIOR_INTEIRO_DO_BANCO)]
IdNaConsulta = Annotated[int | None, Query(le=MAIOR_INTEIRO_DO_BANCO)]
# O deslocamento (pagina - 1) * tamanho_pagina cabe no BIGINT do OFFSET com este teto.
Pagina = Annotated[int, Query(ge=1, le=MAIOR_INTEIRO_DO_BANCO)]
TamanhoPagina = Annotated[int, Query(ge=1, le=100)]
