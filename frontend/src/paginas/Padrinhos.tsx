import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { doacoes as apiDoacoes, padrinhos as api } from '../api/recursos'
import type { Padrinho } from '../api/tipos'
import { Campo } from '../componentes/Campos'
import {
  Aviso,
  CabecalhoPagina,
  Carregando,
  Cpf,
  EstadoVazio,
  Paginacao,
  Selo,
  Sobreposicao,
} from '../componentes/Interface'
import {
  TIPOS_DOACAO,
  cpfValido,
  formatarData,
  formatarMoeda,
  formatarTelefone,
} from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 20

type Painel =
  | { tipo: 'cadastro' }
  | { tipo: 'edicao'; padrinho: Padrinho }
  | { tipo: 'doacoes'; padrinho: Padrinho }

export function Padrinhos() {
  const [pagina, setPagina] = useState(1)
  const [painel, setPainel] = useState<Painel | null>(null)
  const [mensagem, setMensagem] = useState<string | null>(null)

  const { dados, carregando, erro, recarregar } = useRequisicao(
    () => api.listar(pagina, TAMANHO_PAGINA),
    [pagina],
  )

  function concluir(texto: string) {
    setMensagem(texto)
    setPainel(null)
    recarregar()
  }

  return (
    <>
      <CabecalhoPagina
        titulo="Padrinhos"
        descricao="Quem sustenta o abrigo com contribuições pontuais ou recorrentes."
        acao={
          <button type="button" className="botao" onClick={() => setPainel({ tipo: 'cadastro' })}>
            Cadastrar padrinho
          </button>
        }
      />

      {mensagem ? <Aviso tom="sucesso">{mensagem}</Aviso> : null}
      {erro ? <Aviso>{erro}</Aviso> : null}
      {carregando ? <Carregando /> : null}

      {dados && !carregando ? (
        dados.itens.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum padrinho cadastrado"
            descricao="Cadastre quem contribui com o abrigo para vincular as doações a uma pessoa."
            acao={
              <button
                type="button"
                className="botao"
                onClick={() => setPainel({ tipo: 'cadastro' })}
              >
                Cadastrar padrinho
              </button>
            }
          />
        ) : (
          <>
            <div className="tabela-envolucro">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>CPF</th>
                    <th>Contato</th>
                    <th>
                      <span className="so-leitor-tela">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {dados.itens.map((pessoa) => (
                    <tr key={pessoa.id}>
                      <td className="principal">{pessoa.nome}</td>
                      <td>
                        <Cpf valor={pessoa.cpf} />
                      </td>
                      <td>
                        <span className="contato-linha">{pessoa.email}</span>
                        <span className="contato-linha">{formatarTelefone(pessoa.telefone)}</span>
                      </td>
                      <td>
                        <div className="acoes">
                          <button
                            type="button"
                            className="botao"
                            data-tipo="texto"
                            onClick={() => setPainel({ tipo: 'doacoes', padrinho: pessoa })}
                          >
                            Doações
                          </button>
                          <button
                            type="button"
                            className="botao"
                            data-tipo="texto"
                            onClick={() => setPainel({ tipo: 'edicao', padrinho: pessoa })}
                          >
                            Editar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Paginacao
              pagina={dados.pagina}
              tamanhoPagina={dados.tamanho_pagina}
              total={dados.total}
              aoMudar={setPagina}
            />
          </>
        )
      ) : null}

      {painel?.tipo === 'cadastro' ? (
        <FormularioPadrinho
          aoFechar={() => setPainel(null)}
          aoSalvar={() => concluir('Padrinho cadastrado.')}
        />
      ) : null}

      {painel?.tipo === 'edicao' ? (
        <FormularioPadrinho
          padrinho={painel.padrinho}
          aoFechar={() => setPainel(null)}
          aoSalvar={() => concluir('Cadastro do padrinho atualizado.')}
        />
      ) : null}

      {painel?.tipo === 'doacoes' ? (
        <DoacoesDoPadrinho padrinho={painel.padrinho} aoFechar={() => setPainel(null)} />
      ) : null}
    </>
  )
}

/* --- Cadastro e edicao -------------------------------------------------- */

interface FormularioProps {
  padrinho?: Padrinho
  aoFechar: () => void
  aoSalvar: () => void
}

function FormularioPadrinho({ padrinho, aoFechar, aoSalvar }: FormularioProps) {
  const editando = Boolean(padrinho)

  const [nome, setNome] = useState(padrinho?.nome ?? '')
  const [cpf, setCpf] = useState(padrinho?.cpf ?? '')
  const [email, setEmail] = useState(padrinho?.email ?? '')
  const [telefone, setTelefone] = useState(padrinho?.telefone ?? '')

  const [erro, setErro] = useState<string | null>(null)
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({})
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setErrosCampo({})

    if (!editando && !cpfValido(cpf)) {
      setErrosCampo({ cpf: 'CPF inválido: confira os dígitos.' })
      return
    }

    setSalvando(true)
    try {
      if (padrinho) {
        await api.atualizar(padrinho.id, {
          nome: nome.trim(),
          email: email.trim(),
          telefone: telefone.trim(),
        })
      } else {
        await api.criar({ nome: nome.trim(), cpf, email: email.trim(), telefone: telefone.trim() })
      }
      aoSalvar()
    } catch (problema) {
      if (problema instanceof ErroApi) {
        setErro(problema.mensagemDeTela())
        setErrosCampo(problema.porCampo)
      } else {
        setErro('Não foi possível salvar o cadastro.')
      }
      setSalvando(false)
    }
  }

  return (
    <Sobreposicao titulo={editando ? 'Editar padrinho' : 'Cadastrar padrinho'} aoFechar={aoFechar}>
      <form className="formulario" onSubmit={enviar}>
        {erro ? <Aviso>{erro}</Aviso> : null}

        <Campo
          rotulo="Nome completo"
          required
          minLength={2}
          maxLength={150}
          value={nome}
          erro={errosCampo.nome}
          onChange={(evento) => setNome(evento.target.value)}
        />

        {editando ? null : (
          <Campo
            rotulo="CPF"
            required
            inputMode="numeric"
            maxLength={14}
            value={cpf}
            erro={errosCampo.cpf}
            dica="Pode digitar ou colar com pontos e traço."
            onChange={(evento) => setCpf(evento.target.value.replace(/\D/g, '').slice(0, 11))}
          />
        )}

        <div className="formulario-duplo">
          <Campo
            rotulo="E-mail"
            type="email"
            required
            value={email}
            erro={errosCampo.email}
            onChange={(evento) => setEmail(evento.target.value)}
          />
          <Campo
            rotulo="Telefone"
            required
            minLength={8}
            maxLength={20}
            value={telefone}
            erro={errosCampo.telefone}
            onChange={(evento) => setTelefone(evento.target.value)}
          />
        </div>

        <div className="acoes">
          <button type="submit" className="botao" disabled={salvando}>
            {salvando ? 'Salvando…' : editando ? 'Salvar alterações' : 'Cadastrar padrinho'}
          </button>
          <button type="button" className="botao" data-tipo="texto" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </form>
    </Sobreposicao>
  )
}

/* --- Doacoes de um padrinho (RF13) -------------------------------------- */

function DoacoesDoPadrinho({ padrinho, aoFechar }: { padrinho: Padrinho; aoFechar: () => void }) {
  const { dados, carregando, erro } = useRequisicao(
    () => apiDoacoes.listar({ padrinho_id: padrinho.id, tamanho_pagina: 50 }),
    [padrinho.id],
  )

  const total = dados?.itens.reduce((soma, doacao) => soma + Number(doacao.valor), 0) ?? 0

  return (
    <Sobreposicao titulo={`Doações de ${padrinho.nome}`} aoFechar={aoFechar}>
      <div className="pilha-4">
        {carregando ? <Carregando /> : null}
        {erro ? <Aviso>{erro}</Aviso> : null}

        {dados ? (
          dados.itens.length === 0 ? (
            <p className="texto-fraco">Nenhuma doação registrada para este padrinho.</p>
          ) : (
            <>
              <p>
                <strong className="numero-tabular">{formatarMoeda(total)}</strong> em{' '}
                {dados.total === 1 ? '1 doação' : `${dados.total} doações`}.
              </p>
              <div className="tabela-envolucro">
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Tipo</th>
                      <th className="numero">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.itens.map((doacao) => (
                      <tr key={doacao.id}>
                        <td>{formatarData(doacao.data)}</td>
                        <td>
                          <Selo tom={doacao.tipo === 'recorrente' ? 'jade' : 'neutro'}>
                            {TIPOS_DOACAO[doacao.tipo]}
                          </Selo>
                        </td>
                        <td className="numero">{formatarMoeda(doacao.valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )
        ) : null}

        <div className="acoes">
          <button type="button" className="botao" data-tipo="contorno" onClick={aoFechar}>
            Fechar
          </button>
        </div>
      </div>
    </Sobreposicao>
  )
}
