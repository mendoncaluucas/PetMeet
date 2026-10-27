# Histórias e critérios de aceite — Fase 3

> Evolução 2 do N2: **portal de prestação de contas automatizado**
> Itens 3.2 a 3.5 do [Plano de Ação](PLANO-DE-ACAO-N2.md#fase-3--evolução-2-prestação-de-contas--1510-a-2310)
> Redação: Lucas (Backend), para destravar a fase · Revisão de requisitos: Nicholas · Aceite: Willian
> Situação: aprovado pelo Lucas em 15/10/2026 · revisão do Nicholas pendente

Nenhuma história entra em desenvolvimento antes de este documento ser aprovado (DoR do acordo). Cada critério vira pelo menos um teste automatizado. Os critérios marcados com ⚠ cobrem um caso que **quebraria depois** se fosse feito do jeito óbvio.

"Automatizado" quer dizer: o portal é calculado a partir do que a equipe já registra no dia a dia (doações e gastos). Ninguém monta relatório à mão.

---

## 1. Decisões

| # | Decisão | Origem |
|---|---|---|
| D4 | Prestação de contas **pública**, só com **totais**. Sem login de padrinho e sem dado pessoal. | Recomendação do plano |
| D5 | Portal do adotante **fora** do N2 | Recomendação do plano |
| D11 | Apadrinhamento é um **compromisso mensal**: o padrinho combina um valor por mês para um pet. A doação pontual continua sendo só uma doação, sem apadrinhamento. A coluna `frequencia`, herdada e sem uso, sai. | Lucas, 15/10 |
| D12 | Quando a adoção de um pet é **finalizada**, os apadrinhamentos ativos dele são **encerrados** automaticamente, na mesma transação, com a data de hoje | Lucas, 15/10 |
| D13 | Lançamento financeiro errado se corrige por **estorno**: um lançamento negativo, datado do dia da correção e ligado ao original. Vale para **gasto e doação**. O mês já publicado não muda depois. | Lucas, 15/10 |
| D14 | A equipe (admin e voluntário) registra doações, gastos e apadrinhamentos. **Só o admin estorna.** O veterinário não vê a parte financeira. | Lucas, 15/10 |
| D15 | O portal mostra os gastos **por categoria**, nunca pela descrição. A descrição pode trazer nome de pessoa, como "consulta com a Dra. Fulana". Nomes de pets podem aparecer. | Lucas, 15/10 |

---

## 2. Quem faz o quê

| Recurso | Admin | Voluntário | Vet | Público (sem login) |
|---|---|---|---|---|
| Apadrinhamentos: ver, criar, encerrar | sim | sim | — | — |
| Doações: ver e registrar | sim | sim | — | — |
| Gastos: ver e registrar | sim | sim | — | — |
| Estornar doação ou gasto | sim | — | — | — |
| Esperado × recebido dos padrinhos | sim | sim | — | — |
| Portal de prestação de contas | sim | sim | sim | **sim** |

"—" é **403** (ou **401**, sem login). A matriz do veterinário continua sendo verificada pelo teste que lê o OpenAPI.

---

## 3. Histórias

### H7 — Apadrinhamento (item 3.2)

*Como equipe, quero registrar que um padrinho apadrinha um pet com um valor por mês, para saber quanto cada padrinho se comprometeu a doar.*

1. Um apadrinhamento tem: padrinho, pet, **valor mensal** (maior que zero, até 2 casas), **data de início** e **data de fim** (vazia enquanto ativo).
2. ⚠ O mesmo padrinho só tem **um** apadrinhamento **ativo** por pet. Encerrado, pode apadrinhar o mesmo pet de novo (A-08). A segunda tentativa simultânea também recebe **409**.
3. Encerrar grava a data de fim, que não pode ser anterior à de início nem ficar no futuro. Encerrar o que já está encerrado responde **422**.
4. Não se apadrinha pet **adotado** (**422**). Um pet pode ter vários padrinhos.
5. ⚠ Finalizar a adoção encerra os apadrinhamentos ativos do pet na mesma transação (D12). Se a finalização falhar, nenhum apadrinhamento é encerrado.
6. A tela do padrinho mostra os apadrinhamentos dele, ativos e encerrados. A ficha do pet mostra quantos padrinhos ativos ele tem, sem os nomes para o veterinário.
7. Apadrinhamento não se apaga. O valor combinado não se edita: para mudar o valor, encerra-se e abre-se outro, e o histórico do esperado fica correto.

### H8 — Doação com destino (item 3.4)

*Como equipe, quero indicar para qual pet foi uma doação, quando o padrinho diz, para o portal mostrar quanto cada pet recebeu.*

1. A doação ganha um **pet opcional**. Sem pet, ela conta como doação geral da ONG.
2. Ao escolher um padrinho no formulário, a tela sugere o pet quando ele apadrinha exatamente um. Com mais de um, a pessoa escolhe.
3. ⚠ As doações já gravadas continuam válidas, sem pet. A migration não inventa destino para elas.

### H9 — Gastos e estornos (item 3.3)

*Como equipe, quero registrar cada gasto da ONG, para que o portal mostre para onde foi o dinheiro.*

1. Um gasto tem: valor (maior que zero, até 2 casas), data (não futura, dia de Brasília), **categoria**, descrição, pet opcional e quem registrou.
2. Categorias: alimentação, veterinário e medicamentos, vacinas, higiene e limpeza, estrutura e manutenção, transporte, outros.
3. Gasto e doação **não se editam nem se apagam**. O admin **estorna** informando o motivo (D13).
4. ⚠ O estorno é um lançamento **negativo**, com a data do dia em que foi feito, a mesma categoria e o mesmo pet do original, e ligado a ele. O mês do lançamento original não muda: um gasto de setembro estornado em outubro aparece como −valor em outubro.
5. ⚠ Cada lançamento é estornado **uma vez só**, também com dois pedidos ao mesmo tempo. Um estorno não se estorna (**422**).
6. A listagem mostra o lançamento original marcado como estornado e o estorno logo abaixo, com motivo, quem fez e quando.
7. Registro e estorno ficam na auditoria (RF22).

### H10 — Esperado × recebido dos padrinhos (item 3.4)

*Como equipe, quero ver mês a mês quanto cada padrinho combinou e quanto doou, para cobrar quem está atrasado.*

1. Para cada padrinho e cada mês: **esperado** (a soma dos valores mensais dos apadrinhamentos ativos naquele mês), **recebido** (a soma das doações dele naquele mês, já com os estornos) e a diferença.
2. Um apadrinhamento conta no mês se esteve ativo em **algum dia** daquele mês.
3. Situação do mês: **em dia** (recebido ≥ esperado), **parcial** (0 < recebido < esperado), **sem doação** (recebido = 0 com esperado > 0). O mês corrente aparece como **em andamento**, e não como atrasado.
4. ⚠ "Mês" é o mês em Brasília (A-06): uma doação às 22h de 31/10 é de outubro.
5. A tela mostra os últimos 12 meses, com o mais recente primeiro, e destaca os padrinhos com mês **parcial** ou **sem doação**.
6. Tudo calculado no banco. A lista de padrinhos é paginada.

Na implementação (26/10), dois casos que o texto não cobria: mês sem apadrinhamento ativo aparece como **sem compromisso**, e não conta como pendência; o mês corrente já pago aparece como **em dia**, e não como em andamento. A tela fica em **Contribuições**, no menu da equipe.

### H11 — Portal público de prestação de contas (item 3.5)

*Como doador ou visitante, quero ver quanto a ONG arrecadou e gastou, para confiar que o dinheiro foi bem usado.*

1. Página **pública**, sem login: `/transparencia` no painel e uma rota da API fora da autenticação.
2. Últimos 12 meses (o corrente marcado como em andamento): arrecadado, gasto, saldo do mês e saldo acumulado.
3. Gastos de cada mês **por categoria**.
4. **Por pet:** arrecadado com destino ao pet × gasto com o pet, só de pets que tiveram movimento no período.
5. ⚠ A resposta **não traz** nome de padrinho, nome de doador avulso, CPF, descrição de gasto, id de padrinho nem quem registrou (A-11, D15). A API usa schemas públicos próprios, e um teste confere campo a campo que nada além do previsto sai.
6. ⚠ Os estornos entram no mês em que foram feitos (H9.4), então o portal de um mês fechado não muda depois.
7. Valores somados no banco, em `Decimal`. A tela só formata.

---

## 4. Fora desta fase

- Login de padrinho e recibo individual por e-mail.
- Importação de extrato bancário.
- Gráficos elaborados: a primeira versão do portal usa tabelas e barras simples.
- Portal do adotante (D5).

---

## 5. Notas para a implementação

| Ponto | Cuidado |
|---|---|
| A-08 | A tabela `apadrinhamentos` está vazia em todos os ambientes: a migration troca a unicidade por uma parcial (só os ativos), troca `ativo` por `data_fim`, acrescenta `valor_mensal` e tira `frequencia`. Ela confere antes se a tabela está mesmo vazia e recusa se não estiver. |
| Cascata herdada | `Padrinho.apadrinhamentos` e `Pet.apadrinhamentos` usam `cascade="all, delete-orphan"`, e as chaves usam `ondelete=CASCADE`. Isso passa a `RESTRICT`, sem cascata (A-09). |
| Estorno | Fica na mesma tabela do lançamento (`estorno_de_id`), com valor negativo. Totais e portal somam sem filtro especial, e a unicidade parcial em `estorno_de_id` garante um estorno só. |
| `CHECK valor > 0` em doações | Hoje barra valor negativo. O estorno precisa dele: a regra vira "positivo, ou negativo quando é estorno". |
| Mês | `intervalo_do_mes()` e `hoje_na_ong()` de `app/core/tempo.py`, como no Painel |
| Portal | Rota fora do `requer_perfil`, schemas em `app/esquemas/publico.py` que **não herdam** dos internos |
| Contrato | `tipos.ts` muda no mesmo PR de cada schema novo. Os limites do DEF-15 valem para os ids e valores novos, e o teste de contrato vai cobrar isso. |

### Ordem de entrega

| PR | Conteúdo | Histórias |
|---|---|---|
| 5 | Apadrinhamento, encerramento na adoção, doação com destino | H7, H8 |
| 6 | Gastos e estornos (de gasto e de doação) | H9 |
| 7 | Esperado × recebido | H10 |
| 8 | Portal público | H11 |

Em 26/10 o PR 8 passou à frente do 7: o portal é a entrega exigida da evolução 2, e o prazo é 29/10.
