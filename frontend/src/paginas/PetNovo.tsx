import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ErroApi } from '../api/cliente'
import { pets } from '../api/recursos'
import type { EspeciePet, StatusSaudePet } from '../api/tipos'
import { Campo, CampoSelecao, opcoesDe } from '../componentes/Campos'
import { Aviso, CabecalhoPagina } from '../componentes/Interface'
import { ESPECIES, STATUS_SAUDE, dataDeHoje } from '../util/formato'

export function PetNovo() {
  const navegar = useNavigate()

  const [nome, setNome] = useState('')
  const [especie, setEspecie] = useState<EspeciePet>('cachorro')
  const [idade, setIdade] = useState('')
  const [dataResgate, setDataResgate] = useState(dataDeHoje())
  const [statusSaude, setStatusSaude] = useState<StatusSaudePet>('saudavel')
  const [doencaAtual, setDoencaAtual] = useState('')

  const [erro, setErro] = useState<string | null>(null)
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({})
  const [enviando, setEnviando] = useState(false)

  const exigeDoenca = statusSaude === 'em_tratamento_medico'

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setErrosCampo({})

    // Mesma regra do backend (RF16), verificada antes para poupar uma ida a API.
    if (exigeDoenca && !doencaAtual.trim()) {
      setErrosCampo({ doenca_atual: 'Informe qual doença está sendo tratada.' })
      return
    }

    setEnviando(true)
    try {
      const pet = await pets.criar({
        nome: nome.trim(),
        especie,
        idade: Number(idade),
        data_resgate: dataResgate,
        status_saude: statusSaude,
        doenca_atual: exigeDoenca ? doencaAtual.trim() : null,
      })
      navegar(`/pets/${pet.id}`, { replace: true })
    } catch (problema) {
      if (problema instanceof ErroApi) {
        setErro(problema.mensagemDeTela())
        setErrosCampo(problema.porCampo)
      } else {
        setErro('Não foi possível cadastrar o pet.')
      }
      setEnviando(false)
    }
  }

  return (
    <>
      <CabecalhoPagina
        titulo="Cadastrar pet"
        descricao="Abra a ficha do animal que acabou de chegar. A foto pode ser enviada depois, na própria ficha."
        acao={
          <Link to="/pets" className="botao" data-tipo="contorno">
            Voltar para os pets
          </Link>
        }
      />

      <div className="ficha" style={{ maxWidth: '720px' }}>
        <div className="ficha-corpo">
          <form className="formulario" onSubmit={aoEnviar}>
            {erro ? <Aviso>{erro}</Aviso> : null}

            <Campo
              rotulo="Nome"
              required
              maxLength={100}
              value={nome}
              erro={errosCampo.nome}
              onChange={(evento) => setNome(evento.target.value)}
            />

            <div className="formulario-duplo">
              <CampoSelecao
                rotulo="Espécie"
                value={especie}
                erro={errosCampo.especie}
                onChange={(evento) => setEspecie(evento.target.value as EspeciePet)}
              >
                {opcoesDe(ESPECIES)}
              </CampoSelecao>

              <Campo
                rotulo="Idade"
                type="number"
                min={0}
                max={40}
                required
                value={idade}
                erro={errosCampo.idade}
                dica="Em anos. Use 0 para filhotes com menos de um ano."
                onChange={(evento) => setIdade(evento.target.value)}
              />
            </div>

            <Campo
              rotulo="Data do resgate"
              type="date"
              required
              max={dataDeHoje()}
              value={dataResgate}
              erro={errosCampo.data_resgate}
              onChange={(evento) => setDataResgate(evento.target.value)}
            />

            <CampoSelecao
              rotulo="Estado de saúde na chegada"
              value={statusSaude}
              erro={errosCampo.status_saude}
              onChange={(evento) => setStatusSaude(evento.target.value as StatusSaudePet)}
            >
              {opcoesDe(STATUS_SAUDE)}
            </CampoSelecao>

            {exigeDoenca ? (
              <Campo
                rotulo="Doença em tratamento"
                required
                maxLength={255}
                value={doencaAtual}
                erro={errosCampo.doenca_atual}
                dica="Enquanto o pet estiver em tratamento, a adoção não pode ser finalizada."
                onChange={(evento) => setDoencaAtual(evento.target.value)}
              />
            ) : null}

            <div className="acoes">
              <button type="submit" className="botao" disabled={enviando}>
                {enviando ? 'Cadastrando…' : 'Cadastrar pet'}
              </button>
              <Link to="/pets" className="botao" data-tipo="texto">
                Cancelar
              </Link>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
