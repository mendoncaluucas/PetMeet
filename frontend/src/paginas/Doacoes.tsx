import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { doacoes as api, padrinhos as apiPadrinhos } from '../api/recursos'
import type { FrequenciaContribuicao, Padrinho } from '../api/tipos'
import { Campo, CampoSelecao, opcoesDe } from '../componentes/Campos'
import {
  Aviso,
  CabecalhoPagina,
  Carregando,
  EstadoVazio,
  Paginacao,
  Selo,
  Sobreposicao,
} from '../componentes/Interface'
import { TIPOS_DOACAO, dataDeHoje, formatarData, formatarMoeda } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 20

const VALOR_MAXIMO = 99999999.99

export function Doacoes() {
  const [pagina, setPagina] = useState(1)
  const [padrinhoId, setPadrinhoId] = useState('')
  const [registrando, setRegistrando] = useState(false)
  const [mensagem, setMensagem] = useState<string | null>(null)

  const { dados, carregando, erro, recarregar } = useRequisicao(
    () =>
      Promise.all([
        api.listar({
          pagina,
          tamanho_pagina: TAMANHO_PAGINA,
          padrinho_id: padrinhoId ? Number(padrinhoId) : undefined,
        }),
        apiPadrinhos.listar(1, 100),
      ]),
    [pagina, padrinhoId],
  )

  if (carregando && !dados) return <Carregando texto="Carregando doações…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!dados) return null

  const [lista, listaPadrinhos] = dados
  const nomePorId = new Map(listaPadrinhos.itens.map((pessoa) => [pessoa.id, pessoa.nome]))
  const totalDaPagina = lista.itens.reduce((soma, doacao) => soma + Number(doacao.valor), 0)

  return (
    <>
      <CabecalhoPagina
        titulo="Doações"
        descricao="Todo dinheiro que entra, ligado a um padrinho cadastrado ou a um doador avulso."
        acao={
          <button type="button" className="botao" onClick={() => setRegistrando(true)}>
            Registrar doação
          </button>
        }
      />

      {mensagem ? <Aviso tom="sucesso">{mensagem}</Aviso> : null}

      <div className="filtros">
        <CampoSelecao
          rotulo="Padrinho"
          value={padrinhoId}
          onChange={(evento) => {
            setPadrinhoId(evento.target.value)
            setPagina(1)
          }}
        >
          <option value="">Todos os doadores</option>
          {listaPadrinhos.itens.map((pessoa) => (
            <option key={pessoa.id} value={pessoa.id}>
              {pessoa.nome}
            </option>
          ))}
        </CampoSelecao>

        <span className="filtros-resumo">
          {formatarMoeda(totalDaPagina)} nesta página · {lista.total} no total
        </span>
      </div>

      {lista.itens.length === 0 ? (
        <EstadoVazio
          titulo={padrinhoId ? 'Nenhuma doação deste padrinho' : 'Nenhuma doação registrada'}
          descricao={
            padrinhoId
              ? 'Escolha outro padrinho ou registre a primeira contribuição dele.'
              : 'Registre as contribuições recebidas para acompanhar o que entra no abrigo.'
          }
          acao={
            <button type="button" className="botao" onClick={() => setRegistrando(true)}>
              Registrar doação
            </button>
          }
        />
      ) : (
        <>
          <div className="tabela-envolucro">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Quem doou</th>
                  <th>Tipo</th>
                  <th className="numero">Valor</th>
                </tr>
              </thead>
              <tbody>
                {lista.itens.map((doacao) => (
                  <tr key={doacao.id}>
                    <td className="numero-tabular">{formatarData(doacao.data)}</td>
                    <td className="principal">
                      {doacao.padrinho_id
                        ? (nomePorId.get(doacao.padrinho_id) ?? `Padrinho #${doacao.padrinho_id}`)
                        : (doacao.doador_nome ?? 'Doador não identificado')}
                      {doacao.padrinho_id ? null : (
                        <span className="texto-fraco" style={{ display: 'block' }}>
                          doador avulso
                        </span>
                      )}
                    </td>
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

          <Paginacao
            pagina={lista.pagina}
            tamanhoPagina={lista.tamanho_pagina}
            total={lista.total}
            aoMudar={setPagina}
          />
        </>
      )}

      {registrando ? (
        <RegistrarDoacao
          padrinhos={listaPadrinhos.itens}
          aoFechar={() => setRegistrando(false)}
          aoSalvar={() => {
            setMensagem('Doação registrada.')
            setRegistrando(false)
            recarregar()
          }}
        />
      ) : null}
    </>
  )
}

/* --- Registro ----------------------------------------------------------- */

interface RegistroProps {
  padrinhos: Padrinho[]
  aoFechar: () => void
  aoSalvar: () => void
}

function RegistrarDoacao({ padrinhos, aoFechar, aoSalvar }: RegistroProps) {
  // A API exige padrinho_id OU doador_nome; a escolha vem antes dos campos.
  const [origem, setOrigem] = useState<'padrinho' | 'avulso'>(
    padrinhos.length > 0 ? 'padrinho' : 'avulso',
  )
  const [padrinhoId, setPadrinhoId] = useState('')
  const [doadorNome, setDoadorNome] = useState('')
  const [valor, setValor] = useState('')
  const [data, setData] = useState(dataDeHoje())
  const [tipo, setTipo] = useState<FrequenciaContribuicao>('pontual')

  const [erro, setErro] = useState<string | null>(null)
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({})
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setErrosCampo({})

    const numero = Number(valor.replace(',', '.'))
    if (!Number.isFinite(numero) || numero <= 0) {
      setErrosCampo({ valor: 'O valor precisa ser maior que zero.' })
      return
    }
    // O banco guarda ate 99.999.999,99 (Numeric 10,2); a API recusa acima disso (DEF-15).
    if (numero > VALOR_MAXIMO) {
      setErrosCampo({ valor: 'O valor máximo é R$ 99.999.999,99.' })
      return
    }

    setSalvando(true)
    try {
      await api.criar({
        padrinho_id: origem === 'padrinho' ? Number(padrinhoId) : null,
        doador_nome: origem === 'avulso' ? doadorNome.trim() : null,
        valor: numero,
        data,
        tipo,
      })
      aoSalvar()
    } catch (problema) {
      if (problema instanceof ErroApi) {
        setErro(problema.mensagemDeTela())
        setErrosCampo(problema.porCampo)
      } else {
        setErro('Não foi possível registrar a doação.')
      }
      setSalvando(false)
    }
  }

  return (
    <Sobreposicao titulo="Registrar doação" aoFechar={aoFechar}>
      <form className="formulario" onSubmit={enviar}>
        {erro ? <Aviso>{erro}</Aviso> : null}

        <CampoSelecao
          rotulo="Quem doou"
          value={origem}
          onChange={(evento) => setOrigem(evento.target.value as 'padrinho' | 'avulso')}
        >
          <option value="padrinho" disabled={padrinhos.length === 0}>
            Um padrinho cadastrado
          </option>
          <option value="avulso">Um doador avulso</option>
        </CampoSelecao>

        {origem === 'padrinho' ? (
          <CampoSelecao
            rotulo="Padrinho"
            required
            value={padrinhoId}
            erro={errosCampo.padrinho_id}
            onChange={(evento) => setPadrinhoId(evento.target.value)}
          >
            <option value="">Escolha um padrinho</option>
            {padrinhos.map((pessoa) => (
              <option key={pessoa.id} value={pessoa.id}>
                {pessoa.nome}
              </option>
            ))}
          </CampoSelecao>
        ) : (
          <Campo
            rotulo="Nome do doador"
            required
            maxLength={150}
            value={doadorNome}
            erro={errosCampo.doador_nome}
            onChange={(evento) => setDoadorNome(evento.target.value)}
          />
        )}

        <div className="formulario-duplo">
          <Campo
            rotulo="Valor"
            type="number"
            step="0.01"
            min="0.01"
            max={VALOR_MAXIMO}
            required
            inputMode="decimal"
            value={valor}
            erro={errosCampo.valor}
            dica="Em reais."
            onChange={(evento) => setValor(evento.target.value)}
          />
          <Campo
            rotulo="Data"
            type="date"
            required
            max={dataDeHoje()}
            value={data}
            erro={errosCampo.data}
            onChange={(evento) => setData(evento.target.value)}
          />
        </div>

        <CampoSelecao
          rotulo="Tipo de contribuição"
          value={tipo}
          dica="Recorrente é a contribuição que se repete todo mês."
          onChange={(evento) => setTipo(evento.target.value as FrequenciaContribuicao)}
        >
          {opcoesDe(TIPOS_DOACAO)}
        </CampoSelecao>

        <div className="acoes">
          <button type="submit" className="botao" disabled={salvando}>
            {salvando ? 'Registrando…' : 'Registrar doação'}
          </button>
          <button type="button" className="botao" data-tipo="texto" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </form>
    </Sobreposicao>
  )
}
