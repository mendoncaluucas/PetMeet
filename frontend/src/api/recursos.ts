/** Uma funcao por endpoint da API, agrupada como os routers do backend. */

import { consulta, requisitar } from './cliente'
import type {
  Adotante,
  AdotanteCriar,
  Apadrinhamento,
  ApadrinhamentoCriar,
  AlertasVacina,
  AplicacaoCriar,
  AplicacaoVacina,
  Atendimento,
  AtendimentoCriar,
  CartaoVacinacao,
  Doacao,
  DoacaoCriar,
  Gasto,
  GastoCriar,
  CategoriaGasto,
  EspeciePet,
  PadrinhosDoPet,
  PaginaResposta,
  Padrinho,
  PadrinhoCriar,
  Pet,
  PetAtualizar,
  PetAtualizarStatusSaude,
  PetCriar,
  ProcessoAdocao,
  ProcessoAdocaoAtualizarStatus,
  ProcessoAdocaoCriar,
  ResumoPainel,
  SituacaoAdocaoPet,
  StatusSaudePet,
  TokenResposta,
  Usuario,
  UsuarioCriar,
  Vacina,
  VacinaAtualizar,
  VacinaCriar,
} from './tipos'

export const autenticacao = {
  /** POST /auth/login - form-urlencoded, padrao OAuth2 (username = email). */
  entrar: (email: string, senha: string) =>
    requisitar<TokenResposta>('/auth/login', {
      metodo: 'POST',
      semAutenticacao: true,
      formulario: { username: email, password: senha },
    }),

  /** GET /auth/me - quem esta logado e com qual perfil, lido do banco. */
  eu: () => requisitar<Usuario>('/auth/me'),
}

export interface FiltrosPets {
  pagina?: number
  tamanho_pagina?: number
  especie?: EspeciePet | ''
  status_saude?: StatusSaudePet | ''
  situacao_adocao?: SituacaoAdocaoPet | ''
}

export const pets = {
  listar: (filtros: FiltrosPets = {}) =>
    requisitar<PaginaResposta<Pet>>(`/pets${consulta({ ...filtros })}`),

  /** Quantos padrinhos ativos o pet tem; serve a qualquer perfil (sem nomes). */
  padrinhos: (id: number) => requisitar<PadrinhosDoPet>(`/pets/${id}/padrinhos`),

  obter: (id: number) => requisitar<Pet>(`/pets/${id}`),

  criar: (dados: PetCriar) => requisitar<Pet>('/pets', { metodo: 'POST', corpo: dados }),

  atualizar: (id: number, dados: PetAtualizar) =>
    requisitar<Pet>(`/pets/${id}`, { metodo: 'PATCH', corpo: dados }),

  atualizarStatusSaude: (id: number, dados: PetAtualizarStatusSaude) =>
    requisitar<Pet>(`/pets/${id}/status-saude`, { metodo: 'PATCH', corpo: dados }),

  enviarFoto: (id: number, arquivo: File) => {
    const dados = new FormData()
    dados.append('arquivo', arquivo)
    return requisitar<Pet>(`/pets/${id}/foto`, { metodo: 'POST', arquivo: dados })
  },
}

export const adotantes = {
  /**
   * Por padrao a API devolve so os ativos. Telas que usam a lista para dar nome aos
   * processos antigos precisam dos inativos tambem.
   */
  listar: (pagina = 1, tamanho_pagina = 20, incluirInativos = false) =>
    requisitar<PaginaResposta<Adotante>>(
      `/adotantes${consulta({
        pagina,
        tamanho_pagina,
        incluir_inativos: incluirInativos ? 'true' : undefined,
      })}`,
    ),

  obter: (id: number) => requisitar<Adotante>(`/adotantes/${id}`),

  criar: (dados: AdotanteCriar) =>
    requisitar<Adotante>('/adotantes', { metodo: 'POST', corpo: dados }),

  atualizar: (id: number, dados: Partial<AdotanteCriar> & { ativo?: boolean }) =>
    requisitar<Adotante>(`/adotantes/${id}`, { metodo: 'PATCH', corpo: dados }),

  /** So para quem nunca teve processo; com processo a API responde 409 e pede inativar. */
  excluir: (id: number) => requisitar<void>(`/adotantes/${id}`, { metodo: 'DELETE' }),
}

export const padrinhos = {
  listar: (pagina = 1, tamanho_pagina = 20) =>
    requisitar<PaginaResposta<Padrinho>>(`/padrinhos${consulta({ pagina, tamanho_pagina })}`),

  obter: (id: number) => requisitar<Padrinho>(`/padrinhos/${id}`),

  criar: (dados: PadrinhoCriar) =>
    requisitar<Padrinho>('/padrinhos', { metodo: 'POST', corpo: dados }),

  atualizar: (id: number, dados: Partial<PadrinhoCriar>) =>
    requisitar<Padrinho>(`/padrinhos/${id}`, { metodo: 'PATCH', corpo: dados }),
}

export const processos = {
  /** pet_id e adotante_id atendem o historico de adocoes por pet ou por pessoa (RF08). */
  listar: (
    opcoes: {
      pagina?: number
      tamanho_pagina?: number
      pet_id?: number
      adotante_id?: number
    } = {},
  ) => requisitar<PaginaResposta<ProcessoAdocao>>(`/processos-adocao${consulta({ ...opcoes })}`),

  obter: (id: number) => requisitar<ProcessoAdocao>(`/processos-adocao/${id}`),

  criar: (dados: ProcessoAdocaoCriar) =>
    requisitar<ProcessoAdocao>('/processos-adocao', { metodo: 'POST', corpo: dados }),

  atualizarStatus: (id: number, dados: ProcessoAdocaoAtualizarStatus) =>
    requisitar<ProcessoAdocao>(`/processos-adocao/${id}/status`, {
      metodo: 'PATCH',
      corpo: dados,
    }),
}

export const doacoes = {
  listar: (opcoes: { pagina?: number; tamanho_pagina?: number; padrinho_id?: number } = {}) =>
    requisitar<PaginaResposta<Doacao>>(`/doacoes${consulta({ ...opcoes })}`),

  criar: (dados: DoacaoCriar) => requisitar<Doacao>('/doacoes', { metodo: 'POST', corpo: dados }),

  /** So o admin (D14). Lancamento negativo com a data de hoje; a original nao muda. */
  estornar: (id: number, motivo: string) =>
    requisitar<Doacao>(`/doacoes/${id}/estorno`, { metodo: 'POST', corpo: { motivo } }),
}

export const usuarios = {
  /** Restrito a admin (RN06/RF21): quem nao for admin recebe 403. */
  criar: (dados: UsuarioCriar) =>
    requisitar<Usuario>('/usuarios', { metodo: 'POST', corpo: dados }),
}

export const painel = {
  /** Contagens, total de doacoes do mes e listas curtas, tudo calculado no banco. */
  resumo: () => requisitar<ResumoPainel>('/painel/resumo'),
}

export const atendimentos = {
  /** Ficha clinica do pet, do mais recente para o mais antigo, com os anulados. */
  listar: (petId: number, pagina = 1, tamanho_pagina = 20) =>
    requisitar<PaginaResposta<Atendimento>>(
      `/pets/${petId}/atendimentos${consulta({ pagina, tamanho_pagina })}`,
    ),

  /** So o veterinario registra (D7); os demais perfis recebem 403. */
  registrar: (petId: number, dados: AtendimentoCriar) =>
    requisitar<Atendimento>(`/pets/${petId}/atendimentos`, { metodo: 'POST', corpo: dados }),

  /** Nao apaga: o atendimento fica na ficha, marcado como anulado (D8). */
  anular: (id: number, motivo: string) =>
    requisitar<Atendimento>(`/atendimentos/${id}/anulacao`, {
      metodo: 'POST',
      corpo: { motivo },
    }),
}

export const vacinas = {
  /** Catalogo em ordem alfabetica. As inativas so vem quando pedidas. */
  listar: (incluirInativas = false) =>
    requisitar<Vacina[]>(
      `/vacinas${consulta({ incluir_inativas: incluirInativas ? 'true' : undefined })}`,
    ),

  /** Admin e veterinario (D9). Nome repetido, sem diferenciar maiusculas: 409. */
  criar: (dados: VacinaCriar) => requisitar<Vacina>('/vacinas', { metodo: 'POST', corpo: dados }),

  atualizar: (id: number, dados: VacinaAtualizar) =>
    requisitar<Vacina>(`/vacinas/${id}`, { metodo: 'PATCH', corpo: dados }),
}

export const vacinacao = {
  /** Situacao por vacina (pela ultima aplicacao valida) e historico completo. */
  cartao: (petId: number) => requisitar<CartaoVacinacao>(`/pets/${petId}/cartao-vacinacao`),

  /** So o veterinario aplica (D7). Mesma vacina no mesmo dia: 409. */
  registrar: (petId: number, dados: AplicacaoCriar) =>
    requisitar<AplicacaoVacina>(`/pets/${petId}/aplicacoes-vacina`, {
      metodo: 'POST',
      corpo: dados,
    }),

  /** Vencidas e vencendo em ate 30 dias; pet adotado fica de fora (D6). */
  alertas: (limite = 20) => requisitar<AlertasVacina>(`/vacinacao/alertas${consulta({ limite })}`),

  /** Nao apaga: fica no historico, marcada como anulada, e deixa de valer no status. */
  anular: (id: number, motivo: string) =>
    requisitar<AplicacaoVacina>(`/aplicacoes-vacina/${id}/anulacao`, {
      metodo: 'POST',
      corpo: { motivo },
    }),
}

export const apadrinhamentos = {
  /** Ativos primeiro. So a equipe ve (D14). */
  listar: (
    filtros: {
      padrinho_id?: number
      pet_id?: number
      incluir_encerrados?: boolean
      pagina?: number
      tamanho_pagina?: number
    } = {},
  ) =>
    requisitar<PaginaResposta<Apadrinhamento>>(
      `/apadrinhamentos${consulta({
        ...filtros,
        incluir_encerrados: filtros.incluir_encerrados ? 'true' : undefined,
      })}`,
    ),

  /** Um ativo por padrinho e pet (409); pet adotado nao recebe (422). */
  criar: (dados: ApadrinhamentoCriar) =>
    requisitar<Apadrinhamento>('/apadrinhamentos', { metodo: 'POST', corpo: dados }),

  /** O valor nao se edita: para mudar, encerra-se e abre-se outro. */
  encerrar: (id: number, dataFim: string) =>
    requisitar<Apadrinhamento>(`/apadrinhamentos/${id}/encerramento`, {
      metodo: 'POST',
      corpo: { data_fim: dataFim },
    }),
}

export const gastos = {
  /** Mais recentes primeiro; cada estorno logo abaixo do gasto que corrige. */
  listar: (
    filtros: {
      pagina?: number
      tamanho_pagina?: number
      categoria?: CategoriaGasto | ''
      pet_id?: number
    } = {},
  ) => requisitar<PaginaResposta<Gasto>>(`/gastos${consulta({ ...filtros })}`),

  registrar: (dados: GastoCriar) => requisitar<Gasto>('/gastos', { metodo: 'POST', corpo: dados }),

  /** So o admin (D14). Gasto nao se edita nem se apaga: estorna-se. */
  estornar: (id: number, motivo: string) =>
    requisitar<Gasto>(`/gastos/${id}/estorno`, { metodo: 'POST', corpo: { motivo } }),
}
