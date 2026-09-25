import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ErroApi } from '../api/cliente'
import { adotantes as api, pets as apiPets, processos as apiProcessos } from '../api/recursos'
import type { Adotante } from '../api/tipos'
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
  STATUS_PROCESSO,
  TOM_PROCESSO,
  cpfValido,
  formatarData,
  formatarTelefone,
} from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 20

type Painel =
  | { tipo: 'cadastro' }
  | { tipo: 'edicao'; adotante: Adotante }
  | { tipo: 'historico'; adotante: Adotante }

export function Adotantes() {
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
        titulo="Adotantes"
        descricao="Quem já se candidatou a levar um animal daqui. Os dados pessoais ficam cobertos até alguém precisar deles."
        acao={
          <button type="button" className="botao" onClick={() => setPainel({ tipo: 'cadastro' })}>
            Cadastrar adotante
          </button>
        }
      />

      {mensagem ? <Aviso tom="sucesso">{mensagem}</Aviso> : null}
      {erro ? <Aviso>{erro}</Aviso> : null}
      {carregando ? <Carregando /> : null}

      {dados && !carregando ? (
        dados.itens.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum adotante cadastrado"
            descricao="Cadastre a pessoa interessada antes de abrir o processo de adoção."
            acao={
              <button
                type="button"
                className="botao"
                onClick={() => setPainel({ tipo: 'cadastro' })}
              >
                Cadastrar adotante
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
                            onClick={() => setPainel({ tipo: 'historico', adotante: pessoa })}
                          >
                            Histórico
                          </button>
                          <button
                            type="button"
                            className="botao"
                            data-tipo="texto"
                            onClick={() => setPainel({ tipo: 'edicao', adotante: pessoa })}
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
        <FormularioAdotante
          aoFechar={() => setPainel(null)}
          aoSalvar={() => concluir('Adotante cadastrado.')}
        />
      ) : null}

      {painel?.tipo === 'edicao' ? (
        <FormularioAdotante
          adotante={painel.adotante}
          aoFechar={() => setPainel(null)}
          aoSalvar={() => concluir('Cadastro do adotante atualizado.')}
        />
      ) : null}

      {painel?.tipo === 'historico' ? (
        <HistoricoDeAdocoes adotante={painel.adotante} aoFechar={() => setPainel(null)} />
      ) : null}
    </>
  )
}

/* --- Cadastro e edicao -------------------------------------------------- */

interface FormularioProps {
  adotante?: Adotante
  aoFechar: () => void
  aoSalvar: () => void
}

function FormularioAdotante({ adotante, aoFechar, aoSalvar }: FormularioProps) {
  const editando = Boolean(adotante)

  const [nome, setNome] = useState(adotante?.nome ?? '')
  const [cpf, setCpf] = useState(adotante?.cpf ?? '')
  const [email, setEmail] = useState(adotante?.email ?? '')
  const [telefone, setTelefone] = useState(adotante?.telefone ?? '')
  const [endereco, setEndereco] = useState(adotante?.endereco ?? '')

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
      if (adotante) {
        // O CPF nao entra no PATCH: o backend nao aceita troca de CPF.
        await api.atualizar(adotante.id, {
          nome: nome.trim(),
          email: email.trim(),
          telefone: telefone.trim(),
          endereco: endereco.trim(),
        })
      } else {
        await api.criar({
          nome: nome.trim(),
          cpf,
          email: email.trim(),
          telefone: telefone.trim(),
          endereco: endereco.trim(),
        })
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
    <Sobreposicao titulo={editando ? 'Editar adotante' : 'Cadastrar adotante'} aoFechar={aoFechar}>
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

        <Campo
          rotulo="Endereço"
          required
          minLength={5}
          maxLength={255}
          value={endereco}
          erro={errosCampo.endereco}
          dica="Rua, número, bairro e cidade."
          onChange={(evento) => setEndereco(evento.target.value)}
        />

        <div className="acoes">
          <button type="submit" className="botao" disabled={salvando}>
            {salvando ? 'Salvando…' : editando ? 'Salvar alterações' : 'Cadastrar adotante'}
          </button>
          <button type="button" className="botao" data-tipo="texto" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </form>
    </Sobreposicao>
  )
}

/* --- Historico de adocoes (RF08) ---------------------------------------- */

function HistoricoDeAdocoes({ adotante, aoFechar }: { adotante: Adotante; aoFechar: () => void }) {
  const { dados, carregando, erro } = useRequisicao(
    () =>
      Promise.all([
        apiProcessos.listar({ adotante_id: adotante.id, tamanho_pagina: 50 }),
        apiPets.listar({ tamanho_pagina: 100 }),
      ]),
    [adotante.id],
  )

  return (
    <Sobreposicao titulo={`Histórico de ${adotante.nome}`} aoFechar={aoFechar}>
      <div className="pilha-4">
        {carregando ? <Carregando /> : null}
        {erro ? <Aviso>{erro}</Aviso> : null}

        {dados ? (
          dados[0].itens.length === 0 ? (
            <p className="texto-fraco">
              {adotante.nome} ainda não participou de nenhum processo de adoção.
            </p>
          ) : (
            <div className="lista-atencao">
              {dados[0].itens.map((processo) => {
                const pet = dados[1].itens.find((item) => item.id === processo.pet_id)
                return (
                  <div key={processo.id} className="item-atencao" data-saude={pet?.status_saude}>
                    <span>
                      <span className="item-atencao-nome">
                        {pet ? (
                          <Link to={`/pets/${pet.id}`}>{pet.nome}</Link>
                        ) : (
                          `Pet #${processo.pet_id}`
                        )}
                      </span>
                      <span className="item-atencao-detalhe">
                        aberto em {formatarData(processo.criado_em)}
                        {processo.status === 'finalizado'
                          ? `, finalizado em ${formatarData(processo.atualizado_em)}`
                          : ''}
                      </span>
                    </span>
                    <span className="item-atencao-fim">
                      <Selo tom={TOM_PROCESSO[processo.status]}>
                        {STATUS_PROCESSO[processo.status]}
                      </Selo>
                    </span>
                  </div>
                )
              })}
            </div>
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
