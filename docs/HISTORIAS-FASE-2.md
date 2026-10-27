# Histórias e critérios de aceite — Fase 2

> Evolução 1 do N2: **ficha clínica e cartão de vacinação digital com alertas de vencimento**
> Itens 2.2 a 2.6 do [Plano de Ação](PLANO-DE-ACAO-N2.md#fase-2--evolução-1-ficha-clínica-e-cartão-de-vacinação--0810-a-1610)
> Redação: Lucas (Backend), para destravar a fase · Revisão de requisitos: Nicholas · Aceite: Willian
> Situação: aprovado pelo Lucas em 13/10/2026 · revisão do Nicholas pendente

Nenhuma história entra em desenvolvimento antes de este documento ser aprovado (DoR do acordo). Cada critério vira pelo menos um teste automatizado. Os critérios marcados com ⚠ cobrem um caso que **quebraria depois** se fosse feito do jeito óbvio.

---

## 1. Decisões que este documento assume

| # | Decisão | Origem |
|---|---|---|
| D1 | Pet em tratamento médico não finaliza adoção, sem exceção | Lucas, 08/10 — já na `develop` ([PR #13](https://github.com/mendoncaluucas/PetMeet/pull/13)) |
| D2 | Veterinário é um **perfil no painel**, não um portal separado | Recomendação do plano |
| D3 | Alertas **no painel**: vencidas e vencendo em até 30 dias. E-mail fica como extra (2.7) | Recomendação do plano |
| D6 | Pet adotado **não** entra nos alertas da ONG | Recomendação do plano |
| D7 | **Só o veterinário registra** atendimento e aplicação de vacina. A equipe consulta. | Lucas, 13/10 |
| D8 | Registro clínico **não é editado nem apagado**: corrige-se **anulando com motivo** e registrando de novo | Lucas, 13/10 (regra do plano: sem exclusão física de registro clínico) |
| D9 | O catálogo de vacinas já nasce preenchido (via migration) e é mantido pelo admin e pelo veterinário | Lucas, 13/10 |
| D10 | O veterinário tem **página inicial própria**. O resumo atual continua só da equipe, porque mostra nomes de adotantes. | Lucas, 13/10 |

---

## 2. Quem faz o quê

Coluna **Vet** é o perfil novo. "—" significa **403**.

| Recurso | Admin | Voluntário | Vet |
|---|---|---|---|
| Ver pets (lista e ficha) | sim | sim | sim |
| Cadastrar pet, editar dados, enviar foto | sim | sim | — |
| Colocar pet **em** tratamento médico | sim | sim | sim |
| **Tirar** pet de tratamento médico (alta) | — | — | sim |
| Ver ficha clínica e cartão de vacinação | sim | sim | sim |
| Registrar ou anular atendimento e aplicação de vacina | — | — | sim |
| Manter o catálogo de vacinas | sim | — | sim |
| Ver alertas de vacina | sim | sim | sim |
| Resumo do Painel da equipe (`/painel/resumo`) | sim | sim | — |
| Adotantes, padrinhos, doações, processos de adoção | sim | sim | — |
| Equipe (usuários) | sim | — | — |

A autorização é sempre conferida na API. O painel só esconde o que o perfil não pode usar.

---

## 3. Histórias

### H1 — Perfil veterinário (item 2.2)

*Como admin, quero cadastrar um veterinário na equipe, para que ele tenha acesso só ao que é clínico.*

1. Na tela Equipe, o admin escolhe o perfil **Veterinário** ao cadastrar um usuário. A API aceita `perfil: "veterinario"`.
2. O veterinário entra com e-mail e senha como os demais. `GET /auth/me` devolve `perfil: "veterinario"`.
3. Toda rota segue a matriz da seção 2. Uma rota fora da matriz responde **403** ao veterinário, e há teste para cada uma.
4. O menu do veterinário mostra **Início**, **Pets** e **Vacinas** (catálogo). Ele não vê Adoções, Adotantes, Padrinhos, Doações nem Equipe.
5. ⚠ Se o veterinário abrir pela barra de endereço uma tela que não é dele, como `/adotantes`, vê a mensagem *"Seu perfil não tem acesso a esta tela"*. A tela não fica carregando nem mostra erro genérico.
6. O seed cria um veterinário de teste, com as credenciais no README. Rodar o seed de novo não duplica esse usuário.
7. ⚠ A migration do perfil roda no CI pelo caminho real, `alembic upgrade head` seguido do seed com o veterinário. Os testes montam o banco por `create_all` e **não** pegam o erro de valor de enum usado na mesma transação (A-04).

### H2 — Alta médica só pelo veterinário (item 2.3)

*Como ONG, quero que só o veterinário tire um pet de "em tratamento médico", para que ninguém libere para adoção um pet que não teve alta.*

1. A equipe (admin e voluntário) pode colocar um pet **em** tratamento, informando a doença, como hoje.
2. Um pet em tratamento só sai desse status por um veterinário, para "em recuperação" ou "saudável". A equipe recebe **403**, com uma mensagem dizendo que só o veterinário dá alta.
3. Com o pet em tratamento, a equipe pode corrigir a doença informada sem sair do status. ⚠ Doença só com espaços conta como não informada (**422**), senão a correção apagaria o diagnóstico.
4. Entre "saudável" e "em recuperação" a equipe e o veterinário mudam livremente.
5. Toda mudança de status de saúde ou de doença grava uma linha na auditoria. A linha guarda quem fez, quando, o antes e o depois. Pedir o mesmo status e a mesma doença que o pet já tem não grava nada.
6. ⚠ A mudança de status trava o pet (`FOR UPDATE`), a mesma trava da finalização da adoção. Duas mudanças ao mesmo tempo gravam na auditoria um "antes" que bate com o "depois" da anterior. Há teste com duas conexões.
7. ⚠ A auditoria grava datas e enums como texto (`model_dump(mode="json")`), senão a gravação falha (A-05).
8. Na tela do pet, a equipe vê as opções de alta desabilitadas, com o aviso *"Alta só pelo veterinário"*.

### H3 — Ficha clínica (item 2.4)

*Como veterinário, quero registrar cada atendimento do pet, para que o histórico de saúde não dependa de um único campo de texto.*

1. Um atendimento tem: pet, data do atendimento, **anamnese** (obrigatória), diagnóstico e conduta (opcionais) e o veterinário que registrou, preenchido pela API a partir do login e nunca pelo corpo da requisição.
2. ⚠ A data do atendimento não pode estar no futuro. "Hoje" é o dia em Brasília: um atendimento registrado às 22h de 15/10 com data 15/10 é aceito, mesmo com o servidor já em 16/10 UTC (A-06).
3. A ficha lista os atendimentos do mais recente para o mais antigo e mostra quem registrou.
4. Um atendimento não é editado nem apagado. O veterinário pode **anulá-lo** informando o motivo. O atendimento anulado continua na ficha, marcado como anulado, com o motivo, quem anulou e quando.
5. Anular um atendimento já anulado responde **422**.
6. Registrar um atendimento não muda o status de saúde do pet. A alta (H2) é uma ação separada, que fica na mesma tela.
7. A equipe vê a ficha inteira e não vê os botões de registrar e anular.

### H4 — Catálogo de vacinas (item 2.5)

*Como veterinário, quero escolher a vacina de uma lista, para que "V10" e "v10" não virem duas vacinas diferentes (A-10).*

1. Cada vacina do catálogo tem um nome, uma espécie (cachorro, gato ou todas), um intervalo de reforço em dias (opcional) e a situação ativa ou inativa.
2. ⚠ O nome é único sem diferenciar maiúsculas nem espaços nas pontas: cadastrar " v10 " com "V10" já existente responde **409**.
3. O catálogo inicial vem na migration: V8, V10, gripe canina, giárdia e leishmaniose para cachorro; tríplice e quádrupla felina e FeLV para gato; antirrábica para todas as espécies.
4. Uma vacina não é apagada, só **desativada**. A vacina inativa some da lista de novas aplicações e continua no histórico e nos alertas dos pets que já a tomaram.

### H5 — Cartão de vacinação (item 2.5)

*Como veterinário, quero registrar as vacinas aplicadas e a próxima dose, para que o cartão do pet mostre o que está em dia.*

1. Uma aplicação tem: pet, vacina do catálogo, data da aplicação, **próxima dose** (opcional), lote e observação (opcionais) e o veterinário que registrou, preenchido pela API.
2. ⚠ A data da aplicação não pode estar no futuro (dia de Brasília). A próxima dose, quando houver, é **posterior** à aplicação, mas pode estar no passado: é assim que se registra um cartão antigo com dose atrasada.
3. A vacina precisa ser da espécie do pet ou "todas". V10 em gato responde **422**. Vacina inativa também responde **422**.
4. ⚠ A mesma vacina, no mesmo pet e na mesma data, só pode ter uma aplicação válida. A segunda responde **409**, também com duas requisições simultâneas (índice único parcial, que ignora as anuladas).
5. A tela sugere a próxima dose como data da aplicação + intervalo do catálogo. A pessoa pode mudar ou apagar a data. A API grava o que receber.
6. A aplicação é anulada com motivo, igual ao atendimento (H3.4 e H3.5).
7. O cartão mostra, **por vacina**, a última aplicação válida e o status. A vacina vale pela **última** aplicação válida, ordenada pela data da aplicação e, no empate, pela ordem de registro:

   | Próxima dose da última aplicação | Status |
   |---|---|
   | não informada | **sem reforço previsto** |
   | antes de hoje | **vencida** |
   | de hoje até hoje + 30 dias | **vencendo** |
   | depois de hoje + 30 dias | **em dia** |

8. ⚠ Uma aplicação antiga com a próxima dose no passado **não** deixa a vacina vencida se uma dose mais nova já foi aplicada (A-10). Há teste com três aplicações fora de ordem de registro.
9. ⚠ Se a última aplicação for anulada, a vacina volta a valer pela aplicação válida anterior. Se não sobrar nenhuma, ela sai do cartão.
10. Abaixo do resumo por vacina, o cartão mostra o histórico completo, com as anuladas marcadas.

### H6 — Alertas de vencimento (item 2.6)

*Como equipe e como veterinário, quero ver na página inicial as vacinas vencidas e as que vencem em até 30 dias, para agir antes do vencimento.*

1. A API devolve os alertas já calculados no banco. Cada alerta traz o pet, a vacina, a próxima dose, o status e os dias até o vencimento, ou de atraso.
2. Entram só as vacinas **vencidas** e **vencendo** (H5.7), ordenadas pela data da próxima dose. As mais atrasadas vêm primeiro. A resposta traz o total de cada grupo.
3. ⚠ Pet **adotado** não entra (D6). Pet disponível ou em processo de adoção entra.
4. ⚠ "Hoje" é o dia em Brasília (A-06). Há teste com o relógio fixado às 23h de Brasília do último dia antes do vencimento.
5. No Painel da equipe aparece um quadro **Vacinas** com os dois totais e os primeiros alertas. Cada alerta abre o cartão do pet.
6. A página inicial do veterinário (D10) mostra os **pets em tratamento médico**, com a doença, e os **alertas de vacina**. Ela não usa `/painel/resumo`.

---

## 4. Fora desta fase

- Aviso diário por e-mail. É o item 2.7, extra, do Vinicius.
- Anexos, como exames e receitas, além de prescrição, peso e agenda de retorno.
- Alertas para o adotante ou para o padrinho.
- Edição de atendimento ou de aplicação. A correção é por anulação (D8).

---

## 5. Notas para a implementação

| Ponto | Cuidado |
|---|---|
| Migration do perfil | Isolada, só com `ALTER TYPE perfil_usuario ADD VALUE 'veterinario'`. O `env.py` roda todas as migrations pendentes **numa única transação**, então nenhuma migration seguinte pode usar o valor. O downgrade é manual (não existe `DROP VALUE`) e fica documentado. |
| Status de saúde | Hoje `atualizar_status_saude` lê o pet sem trava. A auditoria do H2.6 exige `obter_por_id_com_lock`. |
| Ordem de trava | Pet antes de qualquer outra linha, a mesma ordem da adoção. Evita deadlock entre a alta e a finalização. |
| Datas | Sempre `hoje_na_ong()` de `app/core/tempo.py`. Nunca `date.today()` no servidor nem `toISOString()` no navegador. |
| Cascata | Os registros clínicos novos **não** entram no `cascade="all, delete-orphan"` do `Pet` (A-09). |
| Contrato | `frontend/src/api/tipos.ts` muda no mesmo PR de cada schema novo. |

### Ordem de entrega

| PR | Conteúdo | Histórias |
|---|---|---|
| 1 | Perfil veterinário, matriz de acesso, alta só pelo veterinário, auditoria, veterinário no seed | H1, H2 |
| 2 | Ficha clínica | H3 |
| 3 | Catálogo e cartão de vacinação | H4, H5 |
| 4 | Alertas, quadro no Painel e página inicial do veterinário | H6 |

Cada PR traz backend, testes e a tela correspondente, para que o QA teste a história inteira de uma vez.
