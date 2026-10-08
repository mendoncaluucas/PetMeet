"""Ponto de entrada da API PetMeet."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import obter_configuracoes
from app.core.excecoes import registrar_tratamento_erros
from app.core.logging import configurar_logging
from app.rotas import (
    adotantes,
    auth,
    doacoes,
    padrinhos,
    painel,
    pets,
    processos_adocao,
    usuarios,
)

configuracoes = obter_configuracoes()
configurar_logging()

app = FastAPI(
    title="PetMeet API",
    description="Gestao de adocao e apadrinhamento de pets para ONGs de protecao animal.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=configuracoes.lista_origens_permitidas,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registrar_tratamento_erros(app)

app.mount("/uploads", StaticFiles(directory=configuracoes.DIRETORIO_UPLOADS), name="uploads")

app.include_router(auth.roteador)
app.include_router(usuarios.roteador)
app.include_router(pets.roteador)
app.include_router(adotantes.roteador)
app.include_router(padrinhos.roteador)
app.include_router(processos_adocao.roteador)
app.include_router(doacoes.roteador)
app.include_router(painel.roteador)


@app.get("/saude", tags=["Infra"])
async def verificar_saude() -> dict[str, str]:
    """Healthcheck simples para orquestradores (Docker, k8s, etc.)."""
    return {"status": "ok"}
