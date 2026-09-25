# PetMeet API

Backend da PetMeet — sistema de gestao de adocao e apadrinhamento de pets para
ONGs de protecao animal. Controla fichas medicas, disponibilidade para adocao,
processos de adocao, cadastro de adotantes/padrinhos e doacoes.

Este documento e o ponto de partida para qualquer pessoa (ou time de
front-end/DevOps) continuar o projeto sem depender de quem o escreveu.

## Stack

- **FastAPI** — framework web assincrono
- **PostgreSQL 16** + **SQLAlchemy 2.0 (async)** + **Alembic** — dados e migrations
- **Pydantic v2** — validacao e contratos da API
- **JWT (python-jose) + bcrypt** — autenticacao e hash de senha
- **pytest + pytest-asyncio + httpx** — testes automatizados
- **Ruff + Black + mypy** — lint, formatacao e checagem de tipos

## Arquitetura

```
rotas/        -> endpoints HTTP (FastAPI routers)
esquemas/      -> contratos Pydantic (entrada/saida, validacao)
servicos/      -> regras de negocio (onde vivem as RNs)
repositorios/  -> acesso a dados (SQLAlchemy)
modelos/       -> tabelas (SQLAlchemy ORM)
core/          -> configuracao, seguranca (JWT/bcrypt), tratamento de erros, logging
armazenamento/ -> interface de storage de fotos (implementacao local; troque por S3 se precisar)
```

Fluxo de uma requisicao: `rotas` recebe o HTTP e valida o payload via
`esquemas` -> chama `servicos` (regra de negocio) -> que usa `repositorios`
para ler/escrever no banco via `modelos`. Erros de negocio sao exceções
tipadas em `app/core/excecoes.py`, capturadas por um handler global que
devolve uma resposta JSON padronizada (nunca expõe stacktrace).

Detalhes completos em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) e
[`docs/MODELO_DE_DADOS.md`](docs/MODELO_DE_DADOS.md).

## Pre-requisitos

- Python 3.11+
- PostgreSQL 16 (local ou via Docker)
- Docker + Docker Compose (opcional, mas recomendado)

## Instalacao (ambiente local, sem Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

Ajuste o `.env` se necessario (usuario/senha do Postgres, `SECRET_KEY`, etc).

Suba um Postgres local (ou use `docker compose up -d db` — veja abaixo) e
depois rode as migrations:

```bash
alembic upgrade head
```

Popule dados de exemplo (cria um usuario admin e dois pets):

```bash
python -m scripts.seed
```

Inicie a API:

```bash
uvicorn app.main:app --reload
```

A documentacao interativa (Swagger) fica em `http://localhost:8000/docs`.
Use o botao **Authorize** com o usuario criado pelo seed
(`admin@petmeet.org.br` / `admin123456`) para testar as rotas protegidas.

## Instalacao via Docker Compose (recomendado)

```bash
cp .env.example .env
docker compose up -d
```

Isso sobe o Postgres, aplica as migrations automaticamente e inicia a API em
`http://localhost:8000`. Rode o seed manualmente na primeira vez, se quiser
dados de exemplo:

```bash
docker compose exec api python -m scripts.seed
```

## Variaveis de ambiente

Veja [`.env.example`](.env.example) — todas as variaveis usadas pela
aplicacao estao documentadas ali (RNF16: nada de credencial no codigo-fonte).

## Testes

Os testes usam um banco PostgreSQL **real e separado** (`DATABASE_URL_TESTE`
no `.env`), nao mocks — as regras criticas (RN01, RN02, RNF18) dependem de
constraints e locks reais do banco.

```bash
# crie o banco de teste uma vez (ex.: via psql ou docker compose exec db ...)
createdb petmeet_teste

pytest -v
```

O teste mais importante do projeto e
[`testes/test_processo_adocao.py`](testes/test_processo_adocao.py): cobre a
regra critica do enunciado (RN01/RF16 — pet em tratamento medico so finaliza
adocao com acompanhamento em dia) e a concorrencia (RN02/RF17/RNF18 — dois
processos do mesmo pet nunca finalizam ao mesmo tempo).

## Qualidade de codigo

```bash
ruff check .
black --check .
mypy app
```

## Migrations (Alembic)

```bash
# criar uma nova migration apos alterar um modelo em app/modelos/
alembic revision --autogenerate -m "descricao da mudanca"

# aplicar migrations pendentes
alembic upgrade head

# desfazer a ultima migration
alembic downgrade -1

# conferir se os modelos e as migrations batem (o CI roda e falha se divergirem)
alembic check
```

Revise o arquivo gerado pelo `--autogenerate` antes do commit: ele traz toda
diferenca entre modelos e banco, nao so a mudanca pretendida.

## Autenticacao

`POST /auth/login` recebe `username` (email) e `password` (form
`application/x-www-form-urlencoded`, padrao OAuth2) e retorna um
`access_token` (JWT). Envie esse token em `Authorization: Bearer <token>`
nas demais rotas.

Perfis de usuario: `admin` e `voluntario` — ambos sao "equipe da ONG" e podem
operar cadastros; rotas de criacao de usuarios (`/usuarios`) sao restritas a
`admin`.

## Front-end

O painel web da equipe fica em [`frontend/`](frontend/) — React + TypeScript +
Vite. Instrucoes de instalacao, decisoes de interface e o que ainda depende da
API estao em [`frontend/README.md`](frontend/README.md).

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

Em desenvolvimento o Vite faz proxy de `/api` e `/uploads` para
`http://localhost:8000`, entao nao e preciso mexer em CORS para rodar local.

- CORS liberado por variavel de ambiente (`ORIGENS_PERMITIDAS`) — adicione a
  URL do painel ali quando for publicar.
- Contrato completo (schemas, códigos de erro, exemplos) disponivel em
  `/docs` (Swagger) e `/openapi.json`.
- Fotos de pet ficam acessiveis em `GET /uploads/<arquivo>` apos o upload em
  `POST /pets/{id}/foto`.

## Preparacao para DevOps

- `Dockerfile` + `docker-compose.yml` prontos para rodar localmente ou servir
  de base para um ambiente de producao (ajustar variaveis de ambiente,
  secrets e, se necessario, trocar o volume do Postgres por um servico
  gerenciado).
- `GET /saude` — healthcheck simples para orquestradores.
- Todas as configuracoes sensiveis vem de variaveis de ambiente (RNF16).

## Escopo entregue vs. proximos passos

Este backend entrega o **escopo de alta prioridade**: RF01, RF03, RF04, RF06,
RF09, RF12, RF14-RF18, RF20, RF21 e as regras de negocio criticas (RN01-RN08),
com autenticacao, tratamento de erros centralizado e testes automatizados das
regras criticas.

Pendente para uma proxima fase (arquitetura ja preparada, so falta
implementar as rotas/servicos especificos):

- **RF08** — o painel já monta o histórico por adotante e por pet usando os
  filtros `adotante_id`/`pet_id` de `GET /processos-adocao`. Falta apenas o
  endpoint dedicado de histórico consolidado, se for desejado.
- **RF10/RF11** — associação padrinho↔pet (modelo `Apadrinhamento` já existe
  em `app/modelos/apadrinhamento.py`, falta a camada de serviço/rotas).
- **RF13** — filtros avançados de consulta de doações.
- **RF19** — concluído: o upload está implementado na API e integrado no
  painel (ficha do pet, em `frontend/src/paginas/PetDetalhe.tsx`).
- **RF22** — o modelo `LogAuditoria` já existe; falta instrumentar os
  serviços para gravar cada alteração relevante.
- **RNF06-RNF10, RNF12, RNF15-RNF20** — observabilidade avançada, cache,
  backup/recuperação automatizados e monitoramento de dependências ficam a
  cargo do time de DevOps/infra a partir da base aqui entregue.
