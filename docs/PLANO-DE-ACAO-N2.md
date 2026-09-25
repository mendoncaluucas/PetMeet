# Plano de Ação — N2

> PetMeet · Equipe Draft · Manutenção e Melhoria
> Período: 25/09 a 29/10/2026 · alvo de conclusão: **23/10**
> Ponto de partida: tag [`v1.0`](https://github.com/mendoncaluucas/PetMeet/tree/v1.0), versão recebida da equipe original

Todo defeito e toda armadilha técnica listados aqui foram **reproduzidos contra o código, o banco ou a API em 24 e 25/09** antes de entrar no documento. O que é risco de projeto, ainda não medível porque o código não existe, está marcado como tal.

---

## 1. Objetivo

O enunciado descreve o problema da ONG como *dificuldade em controlar fichas médicas e acompanhar doações recorrentes de padrinhos*. A versão recebida não resolve nenhuma das duas metades — e as duas evoluções exigidas no N2 são exatamente elas.

| Enunciado | Versão recebida |
|---|---|
| Controlar **fichas médicas** | Um campo `status_saude` e um texto `doenca_atual`. Sem histórico, sem atendimento, sem vacina. Qualquer voluntário muda o status. |
| Acompanhar **doações recorrentes de padrinhos** | Doação é um registro solto marcado como `recorrente`. Não há comparação entre o esperado e o recebido, e o vínculo padrinho↔pet não é acessível pela API. |
| **RN crítica:** pet em tratamento médico não pode ter a adoção finalizada | Finaliza, se alguém marcar uma caixa de confirmação. Há ainda um atalho que dispensa o processo. |
| **Evolução:** cartão de vacinação digital com alertas de vencimento | Não existe |
| **Evolução:** portal de prestação de contas automatizado | Não existe. Não há registro de gastos, só de doações. |

O N2 é, portanto, **terminar de resolver o problema que o enunciado propôs**, corrigindo antes o que impede a base de sustentar as evoluções.

---

## 2. Diagnóstico

### 2.1 O que se mantém

- Arquitetura em camadas `rotas → serviços → repositórios → modelos`, tratamento de erros centralizado e configuração por variável de ambiente
- RN02 com `SELECT ... FOR UPDATE` e índice único parcial como rede de segurança
- CI com lint, testes contra Postgres real, build Docker com smoke test e publicação no GHCR
- `ARQUITETURA.md`, `MODELO_DE_DADOS.md` e os dois READMEs, que correspondem ao código

### 2.2 Defeitos reproduzidos

| ID | Defeito | Evidência | Situação |
|---|---|---|---|
| DEF-01 | Projeto não sobe em instalação nova: o SQLAlchemy 2.1 deixou de instalar o `greenlet` | CI da `main` vermelho; container em loop de reinício | **Corrigido** no [PR #1](https://github.com/mendoncaluucas/PetMeet/pull/1) |
| DEF-02 | RN crítica relaxada: pet em tratamento finaliza adoção com a caixa marcada | `PATCH .../status` → 200; o próprio teste da equipe original afirma esse comportamento | Fase 1 |
| DEF-03 | `PATCH /pets/{id}/situacao-adocao` marca como adotado um pet em tratamento, sem processo | 200 com zero processos; exposto na tela do pet | Fase 1 |
| DEF-04 | Voltar um pet "em processo" para "disponível" permite um segundo processo; cancelar o segundo devolve o pet já adotado para "disponível" | Sequência inteira com 200/201 | Fase 1 |
| DEF-05 | Depois do atalho do DEF-03, finalizar o processo responde 409 *"já foi adotado por meio de outro processo"* — sem nenhum outro processo finalizado. O processo fica preso. | 409 com 0 processos finalizados | Fase 1 |
| DEF-06 | Cancelar e finalizar o mesmo processo ao mesmo tempo: as duas requisições recebem 200 | **27 de 30** rodadas; em sequência, a segunda recebe 422 | Fase 1 |
| DEF-07 | Senha acima de 72 bytes derruba o login e o cadastro de usuário com 500 (bcrypt 5.0 passou a lançar `ValueError`) | Login com 80 bytes → 500; cadastro com 90 → 500. O schema aceita até 100 caracteres. | Fase 1 |
| DEF-08 | Dois cadastros simultâneos com o mesmo CPF: o segundo recebe 500 em vez de 409. Mesmo padrão em padrinho e e-mail de usuário. | **4 de 10** rodadas | Fase 1 |
| DEF-09 | Painel, "recebido este mês": o mês é calculado em UTC. A partir das 21h do último dia, mostra o mês seguinte. | `new Date().toISOString()` em 31/10 21:30 → `2026-11` | Fase 1 |
| DEF-10 | Totais do Painel somados no navegador sobre a primeira página (100 registros) | `LIMITE = 100` em `Painel.tsx` | Fase 1 |
| DEF-11 | Seed não é idempotente: rodado de novo, duplica os pets | Rex e Mingau com 2 registros cada | Fase 1 |
| DEF-12 | CPF validado só pela quantidade de dígitos | `088.888.888-88` aceito; o primeiro dígito verificador deveria ser 0 | Fase 1 |
| DEF-13 | Não há exclusão nem inativação de adotante (a API não tem nenhuma rota `DELETE`) | Lista de rotas do OpenAPI | Fase 1 |

### 2.3 Armadilhas técnicas que as mudanças planejadas vão encontrar

Cada linha é algo que **quebraria o plano se fosse feito do jeito óbvio**.

| ID | Onde morde | O que acontece | Tipo | Como evitar |
|---|---|---|---|---|
| A-01 | Primeira migration nova | Modelos e migration `0001` divergem: `alembic check` falha com **19 operações** — 10 colunas `criado_em`/`atualizado_em` viram `NOT NULL` e as constraints únicas de CPF (adotante, padrinho) e e-mail (usuário) são trocadas por índices. Um `--autogenerate`, que é o comando do README, arrasta tudo isso junto. | Medido | Migration `0002` de reconciliação, revisada linha a linha, e `alembic check` no CI |
| A-02 | Correção do DEF-06 | Reler o processo com `select(...).with_for_update()` depois de já tê-lo carregado **devolve o valor antigo** guardado na sessão: o banco dizia `cancelado`, a leitura trouxe `em_analise`. | Medido | `sessao.refresh(obj, with_for_update=True)` ou `populate_existing`, ambos verificados |
| A-03 | Validador de CPF | `AdotanteResposta` e `PadrinhoResposta` herdam o schema de criação, e o validador **roda também na leitura**. Um validador mais rígido derruba com 500 a listagem de qualquer CPF já gravado. | Medido | Validador só nos schemas de criação |
| A-04 | Perfil `veterinario` | Valor novo de enum no Postgres não pode ser usado na mesma transação que o criou (*unsafe use of new value*), e não existe `DROP VALUE`. | Medido | Migration isolada, sem uso do valor na mesma transação; downgrade documentado como manual |
| A-05 | Auditoria (RF22) | A coluna JSON não aceita `date` nem `Decimal`: a gravação falha com `TypeError`. Enum passa. | Medido | Serializar com `model_dump(mode="json")` antes de gravar |
| A-06 | Tudo que depende de "hoje" ou "este mês" | O container roda em UTC. No Windows, `ZoneInfo("America/Sao_Paulo")` falha sem o pacote `tzdata`. No navegador, `toISOString()` é UTC (DEF-09). | Medido | Datas e meses calculados no backend, em `America/Sao_Paulo`; `tzdata` nas dependências |
| A-07 | Lock de dependências | O `uvloop` do `uvicorn[standard]` só é instalado fora do Windows. Um lock gerado na máquina de alguém da equipe sai sem ele, e com o Python 3.13 local contra o 3.12 do CI e do Docker. | Medido (metadados do PyPI) | Lock universal (`uv pip compile --universal`) ou gerado dentro do container |
| A-08 | Apadrinhamento | `UNIQUE (padrinho_id, pet_id)` impede reapadrinhar o mesmo pet depois de encerrar. Não há coluna de valor. A tabela está vazia em todos os ambientes, porque nunca teve rota. | Medido | Unicidade parcial `WHERE ativo` e coluna de valor, enquanto a tabela ainda está vazia |
| A-09 | Qualquer `DELETE` futuro | `Pet` declara `cascade="all, delete-orphan"` nos processos e apadrinhamentos; apadrinhamento cai em cascata com o padrinho e a doação perde o padrinho (`SET NULL`). Um `DELETE` apagaria histórico de adoção e de prestação de contas. | Lido no código | Sem exclusão física de pet, padrinho, doação, gasto ou registro clínico: inativação e estorno |
| A-10 | Alertas de vacina | Uma aplicação antiga com "próxima dose" no passado apareceria como vencida para sempre, mesmo com a dose seguinte já aplicada. Nome de vacina em texto livre separa "V10" de "v10". | Projeto | Status pela **última** aplicação de cada vacina; catálogo de vacinas |
| A-11 | Portal público | `DoacaoResposta` traz `doador_nome` e `padrinho_id`. Reaproveitar os schemas internos no portal expõe dado pessoal. | Projeto | Schemas públicos próprios, só com agregados |
| A-12 | Próxima atualização do Starlette | `HTTP_422_UNPROCESSABLE_ENTITY` está deprecado (aviso em todo `pytest`). Quando for removido, a importação quebra — o mesmo caso do `greenlet`. | Medido | Trocar por `HTTP_422_UNPROCESSABLE_CONTENT` |

### 2.4 Riscos de projeto

| Risco | Nível | Mitigação |
|---|---|---|
| Capacidade do frontend: estreia no papel e quase toda a evolução tem tela nova | **Alto** | Par com quem fez o frontend no N1 nas telas mais pesadas (fase 3) |
| Revisão obrigatória virar gargalo | Médio | Checks do CI obrigatórios e pares de revisão definidos na fase 0 |
| Migrations em paralelo gerando duas "cabeças" no Alembic | Médio | Só o backend cria migration, em sequência; o CI já falha em `alembic upgrade head` com duas cabeças |
| `frontend/src/api/tipos.ts` escrito à mão, fora de sincronia com a API | Médio | Mudou schema da API, atualiza `tipos.ts` no mesmo PR |
| Runner `ubuntu-latest` migra para o Ubuntu 26 em 19/10 | Baixo | Fixar `ubuntu-24.04` na fase 0 |

---

## 3. Decisões

| # | Decisão | Recomendação | Situação |
|---|---|---|---|
| D1 | RN crítica: texto literal ou caixa de confirmação | **Literal** — pet em tratamento não finaliza adoção, sem exceção. Confirmar com o professor, porque a equipe original pode ter combinado outra leitura. | A decidir |
| D2 | Veterinário: perfil no painel ou portal separado | **Perfil no painel.** O controle de acesso por perfil já existe; um portal separado seria outro sistema, com outro login e outro deploy. | A decidir |
| D3 | Alertas de vacina: painel ou e-mail | **Painel obrigatório** (vencidas e vencendo em 30 dias). E-mail diário como extra. | A decidir |
| D4 | Prestação de contas: página pública ou área do padrinho com login | **Pública, com agregados.** Sem login externo e sem dado pessoal. "Automatizado" = gerado a partir dos dados, sem montagem manual. | A decidir |
| D5 | Portal do adotante | **Fora do N2.** Entra só se a fase 3 fechar antes do prazo. | A decidir |
| D6 | Alertas para pet já adotado | **Fora dos alertas** da ONG: a responsabilidade passa ao adotante. | A decidir |

---

## 4. Plano por fase

O backend começa a fase seguinte enquanto o frontend fecha a anterior. Nenhuma história entra em desenvolvimento sem os critérios de aceite escritos (DoR do acordo).

### Fase 0 — Fundação · 25/09 a 30/09

| # | Entrega | Responsável | Referência |
|---|---|---|---|
| 0.1 | Checks do CI obrigatórios na `main` e na `develop` (`Backend`, `Frontend`, `Docker`) | Vinicius | — |
| 0.2 | Convidar os integrantes que faltam; todos aceitarem | Lucas | — |
| 0.3 | Ligar issues; rótulos `bug`, `débito técnico`, `evolução`; registrar DEF-02 a DEF-13 com resultado esperado e obtido | Vinicius e Kaua | Acordo 2.1 e 4.2 |
| 0.4 | **Migration `0002` de reconciliação e `alembic check` no CI** — bloqueia qualquer migration nova | Lucas | A-01 |
| 0.5 | Lock universal de dependências, `tzdata`, troca da constante deprecada do Starlette | Vinicius e Lucas | A-06, A-07, A-12 |
| 0.6 | `.gitattributes` (o índice já está 100% em LF: entra sem diff em massa) e runner `ubuntu-24.04` | Vinicius | — |
| 0.7 | Acordo preenchido com as regras reais do PetMeet (seções 2 a 6) | Willian e equipe | — |
| 0.8 | Fechar D1 a D6 | Willian | Seção 3 |

### Fase 1 — Correções · 01/10 a 07/10

Toda correção entra com um teste que falha antes e passa depois.

| # | Entrega | Responsável | Referência |
|---|---|---|---|
| 1.1 | Situação de adoção deixa de ser editável à mão; índice único parcial para um só processo ativo por pet (a migration confere duplicados antes); cancelar só devolve o pet a "disponível" se ele estava "em processo" | Lucas e Henrique | DEF-03, DEF-04, DEF-05 |
| 1.2 | Concorrência cancelar × finalizar, com teste de duas conexões reais. Depois do teste verde, quebrar a função de 64 linhas. | Lucas | DEF-06, A-02 |
| 1.3 | RN crítica conforme D1: o teste existente é invertido, não apagado; a coluna `acompanhamento_medico_em_dia` fica, por histórico | Lucas e Henrique | DEF-02 |
| 1.4 | CPF com dígitos verificadores, aceitando pontuação; conflito de gravação vira 409 (CPF e e-mail) | Lucas e Henrique | DEF-08, DEF-12, A-03 |
| 1.5 | Senha limitada a 72 bytes no cadastro; login com senha maior responde 401 | Lucas | DEF-07 |
| 1.6 | Excluir adotante sem processo; inativar o que tem | Lucas e Henrique | DEF-13, A-09 |
| 1.7 | Tela de processos explica o fluxo *em análise → aprovado → finalizado* | Henrique | Teste manual de 24/09 |
| 1.8 | `GET /auth/me`; painel mostra só o que o perfil pode fazer (a autorização continua lendo o perfil do banco a cada requisição) | Lucas e Henrique | Pré-requisito da fase 2 |
| 1.9 | Endpoint de resumo com totais calculados no banco e mês em `America/Sao_Paulo`; o Painel passa a usá-lo | Lucas e Henrique | DEF-09, DEF-10, A-06 |
| 1.10 | Seed idempotente | Lucas | DEF-11 |
| 1.11 | `REQUISITOS.md` com as regras herdadas e as novas; `DER.md`, `DEBITOS-TECNICOS.md` e `HANDOFF.md` corrigidos | Nicholas | — |
| 1.12 | Roteiro de testes de regressão da fase | Kaua | Acordo 4.1 |

### Fase 2 — Evolução 1: ficha clínica e cartão de vacinação · 08/10 a 16/10

| # | Entrega | Responsável | Referência |
|---|---|---|---|
| 2.1 | Histórias e critérios de aceite, prontos até 07/10 | Nicholas | DoR |
| 2.2 | Perfil `veterinario` em migration isolada; acesso decidido rota a rota; veterinário no seed | Lucas | A-04 |
| 2.3 | Sair de "em tratamento médico" só pelo veterinário (colocar continua com a equipe, que faz a triagem); cada mudança de saúde gravada na auditoria | Lucas | A-05 |
| 2.4 | Ficha clínica: atendimentos com anamnese, diagnóstico e conduta | Lucas e Henrique | A-09 |
| 2.5 | Cartão de vacinação: catálogo de vacinas, aplicações e próxima dose; status *em dia / vencendo / vencida* pela última aplicação; "hoje" em `America/Sao_Paulo` | Lucas e Henrique | A-06, A-10 |
| 2.6 | Alertas de vencimento no painel inicial | Henrique | D3, D6 |
| 2.7 | *(Extra)* Aviso diário por e-mail | Vinicius | D3 |

### Fase 3 — Evolução 2: prestação de contas · 15/10 a 23/10

| # | Entrega | Responsável | Referência |
|---|---|---|---|
| 3.1 | Histórias e critérios de aceite, prontos até 14/10 | Nicholas | DoR |
| 3.2 | Apadrinhamento: vínculo padrinho↔pet com valor combinado e unicidade só entre ativos | Lucas e Henrique | A-08 |
| 3.3 | Gastos da ONG: valor, data, categoria, pet opcional. Sem exclusão — correção por estorno, com auditoria. | Lucas e Henrique | A-09 |
| 3.4 | Doações recorrentes: esperado de cada padrinho × recebido, mês a mês | Lucas | A-06 |
| 3.5 | Portal público: arrecadado × gasto por mês e por pet, calculado no banco, com schemas públicos próprios e rota fora do login | Henrique e Willian | A-11, D4 |

### Fase 4 — Fechamento · 24/10 a 29/10

| # | Entrega | Responsável |
|---|---|---|
| 4.1 | Roteiro de testes completo, rodado sobre a versão final | Kaua |
| 4.2 | Verificação a partir de um clone limpo, seguindo só o README | Vinicius |
| 4.3 | Release `v2.0` com notas | Vinicius e Lucas |
| 4.4 | Handoff e matriz de papéis | Nicholas |
| 4.5 | Pitch | Willian |

Se a fase 3 fechar em 23/10, a semana seguinte vira margem para o extra 2.7 ou para o portal do adotante (D5).

---

## 5. Regras que valem o N2 inteiro

- Nenhuma migration nova sem `alembic check` limpo. O `--autogenerate` é revisado linha a linha antes do commit.
- Toda correção de defeito entra com um teste que falha antes da correção.
- "Hoje" e "este mês" são calculados no backend, em `America/Sao_Paulo`.
- Dinheiro é `Decimal` no backend e somado no banco; o frontend só formata.
- Sem exclusão física de pet, padrinho, doação, gasto ou registro clínico.
- Mudou um schema da API, `frontend/src/api/tipos.ts` muda no mesmo PR.
- Nenhum job do CI é renomeado sem atualizar a proteção das branches — o nome do job é o nome do check exigido.
- Merge só com o PR aprovado por outro integrante (DoD do acordo).

---

## 6. Evidência por papel

| Papel | Integrante | O que fica no repositório |
|---|---|---|
| Product Owner | Willian Squena | Acordo preenchido, decisões D1–D6 registradas, aceite dos PRs de evolução, pitch |
| Engenheiro de Requisitos | Nicholas Scoz dos Santos | `REQUISITOS.md`, documentos corrigidos, histórias das duas evoluções, handoff |
| Quality Assurance | Kaua Lucindo | Issues de defeito, roteiros de teste, revisão dos testes de regressão |
| Desenvolvedor Frontend | Henrique Cordeiro de Oliveira | Telas novas e corrigidas |
| Desenvolvedor Backend | Lucas Rogério Mendonça | API, migrations, testes |
| DevOps | Vinicius Steuernagel | Checks obrigatórios, lock, runner, issues e rótulos, release, verificação do zero |

---

## 7. Acompanhamento

A execução é acompanhada pelos pull requests e pelas issues. Este documento é atualizado no fim de cada fase: o que entrou, o que escorregou e por quê.
