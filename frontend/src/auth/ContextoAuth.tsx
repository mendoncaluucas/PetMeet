/**
 * Sessao do usuario.
 *
 * O token emitido pelo backend carrega apenas {"sub": email, "exp": ...}
 * (app/core/seguranca.py). O perfil vem de GET /auth/me, que le o banco: o painel
 * usa para mostrar so o que a pessoa pode fazer. Quem decide continua sendo a API,
 * que rele o perfil a cada requisicao -- esconder um botao aqui e so conveniencia.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { EVENTO_SESSAO_EXPIRADA, apagarToken, gravarToken, lerToken } from '../api/cliente'
import { autenticacao } from '../api/recursos'
import type { Usuario } from '../api/tipos'

interface Sessao {
  email: string | null
  autenticado: boolean
  /** null enquanto /auth/me nao respondeu: trate como "perfil ainda desconhecido". */
  usuario: Usuario | null
  /** /auth/me falhou por outro motivo que nao 401: o perfil nao vai chegar sozinho. */
  perfilFalhou: boolean
  ehAdmin: boolean
  entrar: (email: string, senha: string) => Promise<void>
  sair: () => void
}

const ContextoAuth = createContext<Sessao | null>(null)

interface CargaToken {
  sub?: string
  exp?: number
}

function lerCargaDoToken(token: string): CargaToken | null {
  const partes = token.split('.')
  if (partes.length !== 3) return null
  try {
    const base64 = partes[1].replace(/-/g, '+').replace(/_/g, '/')
    const preenchido = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const bytes = Uint8Array.from(atob(preenchido), (caractere) => caractere.charCodeAt(0))
    return JSON.parse(new TextDecoder().decode(bytes)) as CargaToken
  } catch {
    return null
  }
}

function emailDeTokenValido(token: string | null): string | null {
  if (!token) return null
  const carga = lerCargaDoToken(token)
  if (!carga?.sub) return null
  // Token ja vencido: nem tenta usar, vai direto para o login.
  if (carga.exp && carga.exp * 1000 <= Date.now()) return null
  return carga.sub
}

export function ProvedorAuth({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(() => emailDeTokenValido(lerToken()))
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [perfilFalhou, setPerfilFalhou] = useState(false)

  useEffect(() => {
    if (!email) apagarToken()
  }, [email])

  useEffect(() => {
    setUsuario(null)
    setPerfilFalhou(false)
    if (!email) return
    let cancelado = false
    autenticacao
      .eu()
      .then((dados) => {
        if (!cancelado) setUsuario(dados)
      })
      .catch(() => {
        // Um 401 aqui ja encerra a sessao pelo cliente (EVENTO_SESSAO_EXPIRADA). Qualquer
        // outra falha deixa o perfil desconhecido: as telas restritas ficam escondidas e
        // avisam, em vez de esperar para sempre.
        if (!cancelado) setPerfilFalhou(true)
      })
    return () => {
      cancelado = true
    }
  }, [email])

  useEffect(() => {
    const aoExpirar = () => setEmail(null)
    window.addEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar)
    return () => window.removeEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar)
  }, [])

  const entrar = useCallback(async (usuarioLogin: string, senha: string) => {
    const resposta = await autenticacao.entrar(usuarioLogin, senha)
    gravarToken(resposta.access_token)
    setEmail(emailDeTokenValido(resposta.access_token) ?? usuarioLogin)
  }, [])

  const sair = useCallback(() => {
    apagarToken()
    setEmail(null)
  }, [])

  const valor = useMemo<Sessao>(
    () => ({
      email,
      autenticado: email !== null,
      usuario,
      perfilFalhou,
      ehAdmin: usuario?.perfil === 'admin',
      entrar,
      sair,
    }),
    [email, usuario, perfilFalhou, entrar, sair],
  )

  return <ContextoAuth.Provider value={valor}>{children}</ContextoAuth.Provider>
}

// O hook mora junto do provedor de proposito: sao a mesma peca. O aviso abaixo
// e so sobre recarga a quente durante o desenvolvimento.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): Sessao {
  const sessao = useContext(ContextoAuth)
  if (!sessao) throw new Error('useAuth precisa estar dentro de ProvedorAuth')
  return sessao
}
