# DER — Diagrama de Entidade-Relacionamento — PetMeet

> **Documento da `v1.0`, mantido como registro.** Não traz as tabelas do N2 (atendimentos, vacinas, aplicações, gastos e o apadrinhamento mensal). O modelo atual está em [`MODELO_DE_DADOS.md`](MODELO_DE_DADOS.md).

> Modelo de dados reconstruído a partir do domínio descrito no README, nas regras de negócio (RN01–RN08) e nos requisitos funcionais do projeto. **Este documento não substitui `app/modelos/` nem `docs/MODELO_DE_DADOS.md`** — antes de usar em decisões de handoff, valide os nomes exatos de tabelas/colunas, tipos e constraints diretamente no código-fonte e nas migrations do Alembic.

## Diagrama

```mermaid
erDiagram
    USUARIO ||--o{ LOG_AUDITORIA : registra
    PET ||--o{ PROCESSO_ADOCAO : "é objeto de"
    ADOTANTE ||--o{ PROCESSO_ADOCAO : realiza
    PET ||--o{ FICHA_MEDICA : possui
    PET ||--o{ APADRINHAMENTO : recebe
    PADRINHO ||--o{ APADRINHAMENTO : mantém
    ADOTANTE ||--o{ DOACAO : "pode fazer"
    PADRINHO ||--o{ DOACAO : "pode fazer"

    USUARIO {
        int id PK
        string nome
        string email
        string senha_hash
        string perfil "admin | voluntario"
    }

    PET {
        int id PK
        string nome
        string especie
        string raca
        string porte
        string sexo
        string descricao
        bool disponivel_adocao
        string foto_url
    }

    FICHA_MEDICA {
        int id PK
        int pet_id FK
        string descricao
        date data
        bool acompanhamento_em_dia
    }

    ADOTANTE {
        int id PK
        string nome
        string cpf "mascarado nas listagens (RN07/RNF03)"
        string email
        string telefone
        string endereco
    }

    PADRINHO {
        int id PK
        string nome
        string cpf
        string email
        string telefone
    }

    PROCESSO_ADOCAO {
        int id PK
        int pet_id FK
        int adotante_id FK
        string status "em_andamento | finalizado | cancelado"
        date data_inicio
        date data_finalizacao
    }

    APADRINHAMENTO {
        int id PK
        int padrinho_id FK
        int pet_id FK
        decimal valor_mensal
        date data_inicio
        string status
    }

    DOACAO {
        int id PK
        int doador_id FK "nullable — doação pode ser avulsa"
        decimal valor
        date data
        string tipo
    }

    LOG_AUDITORIA {
        int id PK
        int usuario_id FK
        string entidade
        int entidade_id
        string acao
        json dados_antigos
        json dados_novos
        datetime data_hora
    }
```

## Entidades

| Entidade | Descrição | Status na N1 |
|---|---|---|
| **Usuario** | Equipe da ONG. Dois perfis: `admin` e `voluntario`. Criação de usuários restrita a `admin`. | Entregue |
| **Pet** | Ficha do animal disponível para adoção/apadrinhamento, com foto. | Entregue |
| **FichaMedica** | Histórico médico do pet e se o acompanhamento está em dia — base da trava de RN01. | Entregue |
| **Adotante** | Pessoa que adota um pet. CPF mascarado nas listagens (RN07/RNF03). | Entregue |
| **ProcessoAdocao** | Fluxo de adoção entre um Pet e um Adotante, com status e datas. | Entregue |
| **Padrinho** | Pessoa ou empresa que apadrinha um pet (contribuição recorrente). | Cadastro entregue |
| **Apadrinhamento** | Associação Padrinho ↔ Pet. | Modelo pronto; serviço/rotas pendentes (RF10/RF11 — ver `debitos-tecnicos.md`) |
| **Doacao** | Doação avulsa, associada ou não a um doador cadastrado. | Cadastro entregue; filtros avançados pendentes (RF13) |
| **LogAuditoria** | Registro de alterações relevantes feitas por um usuário. | Modelo pronto; instrumentação pendente (RF22) |

## Regras de negócio críticas refletidas no modelo

- **RN01 (RF16):** `ProcessoAdocao.status` só muda para `finalizado` se a `FichaMedica` mais recente do `Pet` tiver `acompanhamento_em_dia = true`.
- **RN02 (RF17 / RNF18):** dois `ProcessoAdocao` do mesmo `Pet` não podem finalizar ao mesmo tempo — tratado com constraint/lock no banco, não apenas validação na aplicação.
- **RN07 (RNF03):** o `cpf` de `Adotante` (e, por extensão, de `Padrinho`) é mascarado nas listagens da API.

## Fonte e validação

Este DER foi montado a partir do README do repositório, das descrições de PRs mergeadas e das regras de negócio documentadas (RN01–RN08). Ele **não foi extraído diretamente de `app/modelos/`**, então nomes de campos, tipos exatos e relacionamentos opcionais (ex.: se `Doacao.doador_id` de fato existe ou se a doação é sempre anônima) devem ser confirmados pelo time que assumir o projeto, cruzando com:

- `app/modelos/` — definição real das tabelas (SQLAlchemy ORM)
- `alembic/` — histórico de migrations
- `docs/MODELO_DE_DADOS.md` — documentação de dados já existente no repositório