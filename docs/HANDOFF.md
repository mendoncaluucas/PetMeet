# Handoff — PetMeet

> **Este é o handoff da `v1.0`, escrito pela equipe original e mantido como registro.** O estado atual, da `v2.0`, está em [`HANDOFF-N2.md`](HANDOFF-N2.md). Vários pontos abaixo já foram resolvidos no N2, como o apadrinhamento e a falta de CI.

> Documento de transição para o time que avaliar a viabilidade de receber este projeto. Reúne o essencial para decidir e, decidindo receber, começar a trabalhar sem depender de quem escreveu o código.

## Identificação

| Campo | Valor |
|---|---|
| Case | PetMeet |
| Equipe | Gabrieli Lembeck, Heloísa Cabral, Henrique Klappoth, Julio de Mattos, Mileine de Freitas, Rodrigo Klappoth |
| Product Owner | Mileine de Freitas |
| Repositório | https://github.com/gabilbck/PetMeet |
| Versão entregue | release v1.0 |

## O que é o PetMeet

Backend (API REST) e painel web para ONGs de proteção animal gerenciarem fichas médicas, disponibilidade para adoção, processos de adoção, cadastro de adotantes/padrinhos e doações — resolvendo o risco de um pet em tratamento médico ser liberado para adoção por engano, e a falta de histórico unificado entre adoção, apadrinhamento e doação.

## Estado da entrega

- **13 requisitos funcionais** de alta prioridade entregues (RF01, RF03, RF04, RF06, RF09, RF12, RF14–RF18, RF20, RF21).
- **8 regras de negócio críticas (RN01–RN08)** implementadas, com testes automatizados contra um PostgreSQL real (não mocks) — necessário porque RN01, RN02 e RNF18 dependem de constraints e locks reais de banco.
- Autenticação JWT, tratamento de erros centralizado (nunca expõe stacktrace) e configuração 100% via variáveis de ambiente (nenhuma credencial no código-fonte).
- Painel web em React + TypeScript + Vite, cobrindo toda a API existente.

Detalhes de arquitetura e stack: ver o pitch (PPTX) e `README.md` do repositório.

## Estrutura do repositório

```
PetMeet/
├── README.md
├── frontend/        → painel React + TypeScript + Vite
├── app/             → API FastAPI (rotas, esquemas, serviços, repositórios, modelos, core, armazenamento)
├── alembic/         → migrations do banco
├── testes/          → testes automatizados (pytest, banco real)
└── docs/
    ├── ARQUITETURA.md
    ├── MODELO_DE_DADOS.md
    ├── DER.md               → este pacote de handoff
    ├── debitos-tecnicos.md  → este pacote de handoff
    └── handoff.md            → este documento
```

## Documentos deste pacote de handoff

- **[`DER.md`](./DER.md)** — modelo de dados (entidades, relacionamentos, regras de negócio refletidas no banco). Reconstruído a partir da documentação existente; validar contra `app/modelos/` e `docs/MODELO_DE_DADOS.md`.
- **[`debitos-tecnicos.md`](./debitos-tecnicos.md)** — o que está pendente (RF10/RF11, RF13, RF22 e os itens de observabilidade/infra), com status e esforço estimado.

## Como começar (ambiente local)

```bash
cp .env.example .env
docker compose up -d
docker compose exec api python -m scripts.seed   # dados de exemplo
```

API em `http://localhost:8000`, documentação interativa (Swagger) em `http://localhost:8000/docs`. Login de teste: `admin@petmeet.org.br` / `admin123456`.

Frontend:
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Gestão do time (N1)

O histórico de commits e pull requests do repositório (19 commits, PRs #1 a #7) serve como evidência complementar do ritmo de entrega.

## Links úteis para avaliação

- Repositório: https://github.com/gabilbck/PetMeet
- Versão entregue: release v1.0

## Pontos de atenção para quem for receber

1. **Apadrinhamento (RF10/RF11)** é o maior gap funcional — o modelo já existe, falta a camada de serviço e as rotas.
2. Os testes das regras críticas **exigem um PostgreSQL real** (`DATABASE_URL_TESTE`) — não rodam com mocks.
3. Observabilidade, cache e backup automatizado ainda não foram implementados; a arquitetura foi preparada para isso, mas a execução fica com o time de DevOps/infra.

Ver `debitos-tecnicos.md` para o detalhamento completo de cada pendência.