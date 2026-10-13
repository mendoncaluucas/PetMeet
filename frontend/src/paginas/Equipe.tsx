import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { usuarios } from '../api/recursos'
import type { PerfilUsuario } from '../api/tipos'
import { Campo, CampoSelecao, opcoesDe } from '../componentes/Campos'
import { Aviso, CabecalhoPagina } from '../componentes/Interface'
import { PERFIS } from '../util/formato'

/**
 * A API tem POST /usuarios, mas nao tem listagem: nao da para mostrar quem ja
 * faz parte da equipe. Enquanto esse endpoint nao existir, esta tela so cria
 * contas - e diz isso em vez de fingir uma lista vazia.
 */
export function Equipe() {
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [perfil, setPerfil] = useState<PerfilUsuario>('voluntario')

  const [erro, setErro] = useState<string | null>(null)
  const [sucesso, setSucesso] = useState<string | null>(null)
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({})
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setSucesso(null)
    setErrosCampo({})

    if (senha.length < 8) {
      setErrosCampo({ senha: 'A senha precisa ter pelo menos 8 caracteres.' })
      return
    }

    setSalvando(true)
    try {
      const criado = await usuarios.criar({
        nome: nome.trim(),
        email: email.trim(),
        senha,
        perfil,
      })
      setSucesso(`${criado.nome} já pode entrar no painel com o e-mail ${criado.email}.`)
      setNome('')
      setEmail('')
      setSenha('')
      setPerfil('voluntario')
    } catch (problema) {
      if (problema instanceof ErroApi) {
        setErro(problema.mensagemDeTela())
        setErrosCampo(problema.porCampo)
      } else {
        setErro('Não foi possível criar a conta.')
      }
    } finally {
      setSalvando(false)
    }
  }

  return (
    <>
      <CabecalhoPagina
        titulo="Equipe"
        descricao="Contas de quem opera o painel. Só administradores da ONG conseguem criar novas contas."
      />

      <div className="ficha" style={{ maxWidth: '640px' }}>
        <div className="ficha-corpo">
          <form className="formulario" onSubmit={enviar}>
            {erro ? <Aviso>{erro}</Aviso> : null}
            {sucesso ? <Aviso tom="sucesso">{sucesso}</Aviso> : null}

            <Campo
              rotulo="Nome"
              required
              minLength={2}
              maxLength={150}
              value={nome}
              erro={errosCampo.nome}
              onChange={(evento) => setNome(evento.target.value)}
            />

            <Campo
              rotulo="E-mail"
              type="email"
              required
              autoComplete="off"
              value={email}
              erro={errosCampo.email}
              dica="É com este e-mail que a pessoa entra no painel."
              onChange={(evento) => setEmail(evento.target.value)}
            />

            <Campo
              rotulo="Senha provisória"
              type="password"
              required
              minLength={8}
              maxLength={100}
              autoComplete="new-password"
              value={senha}
              erro={errosCampo.senha}
              dica="Pelo menos 8 caracteres. Combine com a pessoa e peça que ela troque depois."
              onChange={(evento) => setSenha(evento.target.value)}
            />

            <CampoSelecao
              rotulo="Perfil"
              value={perfil}
              erro={errosCampo.perfil}
              dica="Voluntários operam os cadastros do dia a dia. Administradores também criam contas. Veterinários cuidam da saúde dos pets e são os únicos que dão alta de um tratamento."
              onChange={(evento) => setPerfil(evento.target.value as PerfilUsuario)}
            >
              {opcoesDe(PERFIS)}
            </CampoSelecao>

            <div className="acoes">
              <button type="submit" className="botao" disabled={salvando}>
                {salvando ? 'Criando…' : 'Criar conta'}
              </button>
            </div>
          </form>
        </div>
      </div>

      <p className="texto-fraco" style={{ marginTop: 'var(--e-4)', maxWidth: '62ch' }}>
        A listagem de contas existentes depende de um endpoint que a API ainda não expõe (
        <code>GET /usuarios</code>). Assim que ele existir, esta tela passa a mostrar quem está na
        equipe.
      </p>
    </>
  )
}
