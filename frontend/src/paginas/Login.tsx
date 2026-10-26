import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ErroApi } from '../api/cliente'
import { useAuth } from '../auth/ContextoAuth'
import { Campo } from '../componentes/Campos'
import { Aviso } from '../componentes/Interface'

/**
 * Espaco reservado para a foto do abrigo. Coloque um arquivo em
 * `frontend/public/abrigo.jpg` e ele aparece aqui; sem ele, fica a hachura.
 */
const FOTO_ABRIGO = '/abrigo.jpg'

export function Login() {
  const { entrar } = useAuth()
  const navegar = useNavigate()
  const local = useLocation()

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [foto, setFoto] = useState<string | null>(null)

  // Carrega a foto em memoria antes de exibir, para nao piscar imagem quebrada.
  useEffect(() => {
    const imagem = new Image()
    imagem.onload = () => setFoto(FOTO_ABRIGO)
    imagem.src = FOTO_ABRIGO
  }, [])

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await entrar(email.trim(), senha)
      const destino = (local.state as { destino?: string } | null)?.destino
      navegar(destino && destino !== '/entrar' ? destino : '/', { replace: true })
    } catch (problema) {
      if (problema instanceof ErroApi && problema.status === 401) {
        setErro('E-mail ou senha não conferem. Tente de novo.')
      } else {
        setErro(problema instanceof Error ? problema.message : 'Não foi possível entrar.')
      }
      setEnviando(false)
    }
  }

  return (
    <div className="login">
      <div className="login-imagem">
        {foto ? (
          <img src={foto} alt="" />
        ) : (
          <div className="login-imagem-vazia" aria-hidden="true" />
        )}
        <div className="login-legenda">
          <h1>A ficha de cada animal do abrigo</h1>
          <p>
            Ficha médica, situação de adoção, padrinhos e doações. O registro que a equipe consulta
            de manhã e atualiza durante o dia.
          </p>
        </div>
      </div>

      <div className="login-form">
        <div className="login-form-caixa">
          <p className="login-marca">
            Pet<em>Meet</em>
          </p>

          <div>
            <h2 style={{ fontSize: 'var(--t-lg)' }}>Entrar no painel</h2>
            <p className="texto-fraco" style={{ marginTop: 'var(--e-2)' }}>
              Use o e-mail cadastrado pela administração da ONG.
            </p>
          </div>

          {erro ? <Aviso>{erro}</Aviso> : null}

          <form className="formulario" onSubmit={aoEnviar}>
            <Campo
              rotulo="E-mail"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(evento) => setEmail(evento.target.value)}
            />
            <Campo
              rotulo="Senha"
              type="password"
              autoComplete="current-password"
              required
              value={senha}
              onChange={(evento) => setSenha(evento.target.value)}
            />
            <button type="submit" className="botao" disabled={enviando}>
              {enviando ? 'Entrando…' : 'Entrar'}
            </button>
          </form>

          <p className="texto-fraco">
            Perdeu o acesso? Um administrador da ONG cadastra e redefine contas da equipe.
          </p>

          <p className="texto-fraco">
            Quer saber como as doações são usadas?{' '}
            <Link to="/transparencia">Veja a prestação de contas</Link>.
          </p>
        </div>
      </div>
    </div>
  )
}
