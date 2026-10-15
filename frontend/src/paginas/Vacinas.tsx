/**
 * Catalogo de vacinas (fase 2, H4). Todos consultam; admin e veterinario mantem (D9).
 * Vacina nao se apaga: desativada, sai das aplicacoes novas e continua nos cartoes.
 */

import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { vacinas } from '../api/recursos'
import type { EspeciePet, Vacina } from '../api/tipos'
import { useAuth } from '../auth/ContextoAuth'
import { Campo, CampoMarcador, CampoSelecao } from '../componentes/Campos'
import { Aviso, CabecalhoPagina, Carregando, EstadoVazio, Selo } from '../componentes/Interface'
import { ESPECIES } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

export function Vacinas() {
  const { usuario } = useAuth()
  const podeManter = usuario?.perfil === 'admin' || usuario?.perfil === 'veterinario'
  const [mostrarInativas, setMostrarInativas] = useState(false)
  const [cadastrando, setCadastrando] = useState(false)
  const [editando, setEditando] = useState<number | null>(null)
  const [mensagem, setMensagem] = useState<{ tom: 'sucesso' | 'erro'; texto: string } | null>(null)
  const { dados, carregando, erro, recarregar } = useRequisicao(
    () => vacinas.listar(mostrarInativas),
    [mostrarInativas],
  )

  function concluir(texto: string) {
    setCadastrando(false)
    setEditando(null)
    setMensagem({ tom: 'sucesso', texto })
    recarregar()
  }

  function falhar(problema: unknown, padrao: string) {
    setMensagem({
      tom: 'erro',
      texto: problema instanceof ErroApi ? problema.mensagemDeTela() : padrao,
    })
  }

  async function alternarAtiva(vacina: Vacina) {
    try {
      await vacinas.atualizar(vacina.id, { ativa: !vacina.ativa })
      concluir(
        vacina.ativa
          ? `${vacina.nome} desativada. Ela continua nos cartões de quem já tomou.`
          : `${vacina.nome} reativada.`,
      )
    } catch (problema) {
      falhar(problema, 'Não foi possível alterar a vacina.')
    }
  }

  return (
    <>
      <CabecalhoPagina
        titulo="Vacinas"
        descricao="O catálogo de onde o veterinário escolhe a vacina aplicada. Uma lista só, para “V10” e “v10” não virarem duas vacinas."
        acao={
          podeManter ? (
            <button type="button" className="botao" onClick={() => setCadastrando(!cadastrando)}>
              {cadastrando ? 'Fechar' : 'Cadastrar vacina'}
            </button>
          ) : undefined
        }
      />

      {mensagem ? <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso> : null}

      {cadastrando ? (
        <section className="ficha">
          <div className="ficha-corpo">
            <FormularioVacina
              aoSalvar={(nome) => concluir(`${nome} cadastrada no catálogo.`)}
              aoFalhar={(problema) => falhar(problema, 'Não foi possível cadastrar.')}
              aoCancelar={() => setCadastrando(false)}
            />
          </div>
        </section>
      ) : null}

      <CampoMarcador
        rotulo="Mostrar inativas"
        dica="Inativas não aparecem na escolha de vacina ao registrar uma aplicação."
        checked={mostrarInativas}
        onChange={(evento) => setMostrarInativas(evento.target.checked)}
      />

      {carregando ? <Carregando /> : null}
      {erro ? <Aviso>{erro}</Aviso> : null}

      {dados && !carregando ? (
        dados.length === 0 ? (
          <EstadoVazio
            titulo="Nenhuma vacina no catálogo"
            descricao="Cadastre as vacinas usadas pela ONG antes de registrar aplicações."
          />
        ) : (
          <div className="tabela-envolucro">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Vacina</th>
                  <th>Espécie</th>
                  <th>Reforço</th>
                  {podeManter ? (
                    <th>
                      <span className="so-leitor-tela">Ações</span>
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {dados.map((vacina) =>
                  editando === vacina.id ? (
                    <tr key={vacina.id}>
                      <td colSpan={4}>
                        <EdicaoVacina
                          vacina={vacina}
                          aoSalvar={() => concluir(`${vacina.nome} atualizada.`)}
                          aoFalhar={(problema) => falhar(problema, 'Não foi possível salvar.')}
                          aoCancelar={() => setEditando(null)}
                        />
                      </td>
                    </tr>
                  ) : (
                    <tr key={vacina.id}>
                      <td className="principal">
                        {vacina.nome} {vacina.ativa ? null : <Selo>Inativa</Selo>}
                      </td>
                      <td>{vacina.especie ? ESPECIES[vacina.especie] : 'Todas'}</td>
                      <td>
                        {vacina.intervalo_reforco_dias
                          ? `a cada ${vacina.intervalo_reforco_dias} dias`
                          : 'sem reforço'}
                      </td>
                      {podeManter ? (
                        <td>
                          <div className="acoes">
                            <button
                              type="button"
                              className="botao"
                              data-tipo="texto"
                              onClick={() => setEditando(vacina.id)}
                            >
                              Editar
                            </button>
                            <button
                              type="button"
                              className="botao"
                              data-tipo="texto"
                              onClick={() => alternarAtiva(vacina)}
                            >
                              {vacina.ativa ? 'Desativar' : 'Reativar'}
                            </button>
                          </div>
                        </td>
                      ) : null}
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )
      ) : null}
    </>
  )
}

/* --- Formularios ------------------------------------------------------ */

/** "" vira null: o campo vazio quer dizer "sem reforco previsto". */
function lerIntervalo(texto: string): number | null {
  const valor = Number(texto)
  return texto.trim() && Number.isInteger(valor) && valor > 0 ? valor : null
}

interface FormProps {
  aoSalvar: (nome: string) => void
  aoFalhar: (problema: unknown) => void
  aoCancelar: () => void
}

function FormularioVacina({ aoSalvar, aoFalhar, aoCancelar }: FormProps) {
  const [nome, setNome] = useState('')
  const [especie, setEspecie] = useState<EspeciePet | ''>('')
  const [intervalo, setIntervalo] = useState('365')
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setSalvando(true)
    try {
      const vacina = await vacinas.criar({
        nome: nome.trim(),
        especie: especie || null,
        intervalo_reforco_dias: lerIntervalo(intervalo),
      })
      aoSalvar(vacina.nome)
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <Campo
        rotulo="Nome"
        required
        maxLength={100}
        value={nome}
        onChange={(e) => setNome(e.target.value)}
      />
      <CampoSelecao
        rotulo="Espécie"
        value={especie}
        dica="A espécie não muda depois: as aplicações já feitas dependem dela."
        onChange={(e) => setEspecie(e.target.value as EspeciePet | '')}
      >
        <option value="">Todas</option>
        <option value="cachorro">{ESPECIES.cachorro}</option>
        <option value="gato">{ESPECIES.gato}</option>
        <option value="outro">{ESPECIES.outro}</option>
      </CampoSelecao>
      <Campo
        rotulo="Reforço a cada (dias)"
        type="number"
        min={1}
        max={3650}
        value={intervalo}
        dica="Sugere a próxima dose ao registrar uma aplicação. Vazio: sem reforço."
        onChange={(e) => setIntervalo(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Cadastrar vacina'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

interface EdicaoProps extends FormProps {
  vacina: Vacina
}

function EdicaoVacina({ vacina, aoSalvar, aoFalhar, aoCancelar }: EdicaoProps) {
  const [nome, setNome] = useState(vacina.nome)
  const [intervalo, setIntervalo] = useState(String(vacina.intervalo_reforco_dias ?? ''))
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setSalvando(true)
    try {
      const atualizada = await vacinas.atualizar(vacina.id, {
        nome: nome.trim(),
        intervalo_reforco_dias: lerIntervalo(intervalo),
      })
      aoSalvar(atualizada.nome)
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <Campo
        rotulo="Nome"
        required
        maxLength={100}
        value={nome}
        onChange={(e) => setNome(e.target.value)}
      />
      <Campo
        rotulo="Reforço a cada (dias)"
        type="number"
        min={1}
        max={3650}
        value={intervalo}
        dica="Vazio: sem reforço previsto."
        onChange={(e) => setIntervalo(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Salvar'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
