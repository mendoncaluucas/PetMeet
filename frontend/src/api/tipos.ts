/**
 * Espelho dos contratos Pydantic do backend (app/esquemas/*.py).
 * Se um schema mudar la, mude aqui tambem - e o unico ponto de acoplamento.
 */

export type PerfilUsuario = 'admin' | 'voluntario'
export type EspeciePet = 'cachorro' | 'gato' | 'outro'
export type StatusSaudePet = 'saudavel' | 'em_tratamento_medico' | 'em_recuperacao'
export type SituacaoAdocaoPet = 'disponivel' | 'em_processo_adocao' | 'adotado'
export type StatusProcessoAdocao = 'em_analise' | 'aprovado' | 'finalizado' | 'cancelado'
export type FrequenciaContribuicao = 'pontual' | 'recorrente'

export interface PaginaResposta<T> {
  itens: T[]
  total: number
  pagina: number
  tamanho_pagina: number
}

export interface TokenResposta {
  access_token: string
  token_type: string
}

export interface Pet {
  id: number
  nome: string
  especie: EspeciePet
  idade: number
  data_resgate: string
  status_saude: StatusSaudePet
  doenca_atual: string | null
  situacao_adocao: SituacaoAdocaoPet
  foto_url: string | null
  criado_em: string
  atualizado_em: string
}

export interface PetCriar {
  nome: string
  especie: EspeciePet
  idade: number
  data_resgate: string
  status_saude: StatusSaudePet
  doenca_atual?: string | null
}

export interface PetAtualizar {
  nome?: string
  especie?: EspeciePet
  idade?: number
  data_resgate?: string
}

export interface PetAtualizarStatusSaude {
  status_saude: StatusSaudePet
  doenca_atual?: string | null
}

export interface Adotante {
  id: number
  nome: string
  cpf: string
  email: string
  telefone: string
  endereco: string
  /** Inativo: fora das listagens e sem processo novo. */
  ativo: boolean
  criado_em: string
}

export interface AdotanteCriar {
  nome: string
  cpf: string
  email: string
  telefone: string
  endereco: string
}

export interface Padrinho {
  id: number
  nome: string
  cpf: string
  email: string
  telefone: string
  criado_em: string
}

export interface PadrinhoCriar {
  nome: string
  cpf: string
  email: string
  telefone: string
}

export interface ProcessoAdocao {
  id: number
  pet_id: number
  adotante_id: number
  responsavel_id: number | null
  status: StatusProcessoAdocao
  acompanhamento_medico_em_dia: boolean
  criado_em: string
  atualizado_em: string
}

export interface ProcessoAdocaoCriar {
  pet_id: number
  adotante_id: number
}

export interface ProcessoAdocaoAtualizarStatus {
  status: StatusProcessoAdocao
  acompanhamento_medico_em_dia: boolean
}

export interface Doacao {
  id: number
  padrinho_id: number | null
  doador_nome: string | null
  valor: string
  data: string
  tipo: FrequenciaContribuicao
  criado_em: string
}

export interface DoacaoCriar {
  padrinho_id?: number | null
  doador_nome?: string | null
  valor: number
  data: string
  tipo: FrequenciaContribuicao
}

export interface Usuario {
  id: number
  nome: string
  email: string
  perfil: PerfilUsuario
  ativo: boolean
  criado_em: string
}

export interface UsuarioCriar {
  nome: string
  email: string
  senha: string
  perfil: PerfilUsuario
}
