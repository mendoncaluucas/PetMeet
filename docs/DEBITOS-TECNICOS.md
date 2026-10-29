# Débito Técnico da PetMeet API

[#debito-tecnico-da-petmeet-api](#debito-tecnico-da-petmeet-api)

Este documento lista os débitos técnicos conhecidos do projeto, organizados por
impacto. Serve como referência para quem for priorizar o backlog de uma
próxima fase (RF/RNF pendentes) e para registrar pontos de risco que não
aparecem no README.

## Situação na v2.0 (N2, 26/10/2026)

A lista abaixo é a da equipe original, na `v1.0`. O que o N2 fez com cada item:

| # | Débito | Situação na v2.0 |
|---|---|---|
| 1 | RF22 — Auditoria | **Parcial.** Grava as mudanças de saúde do pet e o registro e o estorno de doações e gastos (`app/servicos/auditoria.py`). Faltam processos de adoção, usuários e uma rota de consulta |
| 2 | Observabilidade, cache e backup | Sem mudança |
| 3 | Ausência de CI | **Resolvido.** O item já estava desatualizado na `v1.0`: o `.github/workflows/ci-cd.yml` entrou em 16/09, um dia antes deste documento, mas falhava na `main` (DEF-01) e não bloqueava merge. No N2 ele ficou verde, ganhou `alembic check`, seed e a `develop`, e os checks passaram a ser obrigatórios na `main` e na `develop` |
| 4 | RF10/RF11 — Apadrinhamento | **Resolvido** no PR [#19](https://github.com/mendoncaluucas/PetMeet/pull/19): apadrinhamento mensal, com esperado × recebido no [#22](https://github.com/mendoncaluucas/PetMeet/pull/22) |
| 5 | Fotos só em disco local | Sem mudança |
| 6 | RF08 — Histórico consolidado | Sem mudança |
| 7 | RF13 — Filtros de doações | Sem mudança: a listagem filtra só por padrinho |
| 8 | CORS manual | Sem mudança |

Débitos novos, achados ou criados no N2, ficam no [Plano de Ação](PLANO-DE-ACAO-N2.md#7-acompanhamento) e no [handoff da v2.0](HANDOFF-N2.md#onde-o-projeto-morde).

## Resumo

[#resumo](#resumo)

| # | Débito | Categoria | Impacto | Ação sugerida |
|---|---|---|---|---|
| 1 | RF22 — Auditoria não instrumentada | Funcional | Alto | Instrumentar serviços (`processo_adocao`, `usuarios`, `pets`) para gravar em `LogAuditoria` |
| 2 | RNF06-10, 12, 15-20 — Observabilidade, cache e backup ausentes | Infra | Alto | Priorizar logging estruturado e backup antes de deploy real |
| 3 | Ausência de pipeline de CI | Processo | Alto | Workflow rodando `ruff`/`black`/`mypy`/`pytest` a cada push/PR |
| 4 | RF10/RF11 — Apadrinhamento incompleto | Funcional | Médio | Implementar `servicos/` e rotas para o modelo `Apadrinhamento` já existente |
| 5 | Armazenamento de fotos só em disco local | Infra | Médio | Implementar `armazenamento/s3.py` seguindo a interface já definida |
| 6 | RF08 — Histórico consolidado | Funcional | Baixo | Endpoint dedicado (hoje contornável via filtros de `GET /processos-adocao`) |
| 7 | RF13 — Filtros avançados de doações | Funcional | Baixo | Adicionar filtros por período/valor/status |
| 8 | CORS manual via `ORIGENS_PERMITIDAS` | Operacional | Baixo | Documentar/checklist de deploy para não esquecer de atualizar |

## Como priorizamos

[#como-priorizamos](#como-priorizamos)

- **Alto** — afeta rastreabilidade, confiabilidade em produção ou qualidade
do processo de entrega.
- **Médio** — funcionalidade incompleta ou limitação de escala conhecida,
sem risco imediato.
- **Baixo** — conveniência ou ponto operacional de fácil correção.

## Débitos de Alto impacto

[#debitos-de-alto-impacto](#debitos-de-alto-impacto)

### RF22 — Auditoria não instrumentada

O modelo `LogAuditoria` já existe em `app/modelos/`, mas nenhum serviço grava
nele. Alterações relevantes (mudança de status de processo, edição de
cadastro, etc.) não deixam rastro. Sistema fica sem histórico de quem alterou
o quê.

**Ação sugerida:** instrumentar os serviços críticos (`processo_adocao`,
`usuarios`, `pets`) para gravar um registro de auditoria a cada alteração de
estado relevante.

### RNF06-RNF10, RNF12, RNF15-RNF20 — Observabilidade, cache e backup ausentes

Nenhuma dessas RNFs foi implementada nesta fase: sem métricas, sem logging
estruturado além do básico, sem cache, sem rotina de backup/recuperação
automatizada, sem monitoramento de dependências externas.

**Ação sugerida:** ficou explicitamente a cargo do time de DevOps/infra a
partir da base entregue (Dockerfile + docker-compose já preparados). Priorizar
logging estruturado e backup antes de qualquer deploy real.

### Ausência de pipeline de CI

Não há `.github/workflows` no repositório. `ruff`, `black`, `mypy` e `pytest`
existem e funcionam, mas só rodam manualmente — nada impede um merge que
quebre lint, tipos ou testes.

**Ação sugerida:** workflow simples de CI rodando os três comandos de
qualidade + `pytest` a cada push/PR na `main`.

## Débitos de Médio impacto

[#debitos-de-medio-impacto](#debitos-de-medio-impacto)

### RF10/RF11 — Apadrinhamento incompleto

O modelo `Apadrinhamento` já existe em `app/modelos/apadrinhamento.py`, mas
falta a camada de `servicos/` e as rotas correspondentes. Funcionalidade
modelada no banco, mas inacessível pela API.

### Armazenamento de fotos só em disco local

`app/armazenamento/local.py` é a única implementação da interface
`app/armazenamento/base.py`. Funciona bem para o escopo atual, mas não
escala para múltiplas instâncias/produção. A interface já foi desenhada para
suportar S3 (`armazenamento/s3.py` seria a implementação natural), mas isso
ainda não existe.

## Débitos de Baixo impacto

[#debitos-de-baixo-impacto](#debitos-de-baixo-impacto)

### RF08 — Histórico consolidado

Hoje é possível montar o histórico por adotante ou por pet usando os filtros
`adotante_id`/`pet_id` de `GET /processos-adocao`. Falta apenas um endpoint
dedicado, se for desejado.

### RF13 — Filtros avançados de doações

Consulta de doações ainda não tem filtros avançados (período, valor, status).

### CORS configurado manualmente via variável de ambiente

`ORIGENS_PERMITIDAS` precisa ser lembrada e atualizada manualmente a cada
publicação de um novo front-end/domínio. Baixo risco, mas fácil de esquecer.

## Não coberto por este documento

[#nao-coberto-por-este-documento](#nao-coberto-por-este-documento)

Este levantamento foi feito a partir do README e do `docs/ARQUITETURA.md`.
Não inclui uma varredura de comentários `TODO`/`FIXME` no código-fonte — vale
fazer essa checagem antes de fechar o backlog definitivo.
