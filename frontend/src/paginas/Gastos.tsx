/**
 * Gastos da ONG (fase 3, H9). A equipe registra; so o admin estorna (D14). E daqui que o
 * portal de prestacao de contas tira o "para onde foi o dinheiro", por categoria.
 */

import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { gastos as api, pets as apiPets } from '../api/recursos'
import type { CategoriaGasto } from '../api/tipos'
import { useAuth } from '../auth/ContextoAuth'
import { Campo, CampoSelecao, opcoesDe } from '../componentes/Campos'
import { EstornarLancamento, SituacaoDoLancamento } from '../componentes/Estorno'
import {
  Aviso,
  CabecalhoPagina,
  Carregando,
  EstadoVazio,
  Paginacao,
  Sobreposicao,
} from '../componentes/Interface'
import { CATEGORIAS_GASTO, dataDeHoje, formatarData, formatarMoeda } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 20
const VALOR_MAXIMO = 99999999.99

export function Gastos() {
  const { ehAdmin } = useAuth()
  const [pagina, setPagina] = useState(1)
  const [categoria, setCategoria] = useState<CategoriaGasto | ''>('')
  const [registrando, setRegistrando] = useState(false)
  const [mensagem, setMensagem] = useState<{ tom: 'sucesso' | 'erro'; texto: string } | null>(null)

  const { dados, carregando, erro, recarregar } = useRequisicao(
    () => api.listar({ pagina, tamanho_pagina: TAMANHO_PAGINA, categoria }),
    [pagina, categoria],
  )

  function concluir(texto: string) {
    setRegistrando(false)
    setMensagem({ tom: 'sucesso', texto })
    recarregar()
  }

  return (
    <>
      <CabecalhoPagina
        titulo="Gastos"
        descricao="Para onde vai o dinheiro do abrigo. O portal de transparência mostra estes valores por categoria."
        acao={
          <button type="button" className="botao" onClick={() => setRegistrando(true)}>
            Registrar gasto
          </button>
        }
      />

      {mensagem ? <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso> : null}

      <div className="filtros">
        <CampoSelecao
          rotulo="Categoria"
          value={categoria}
          onChange={(evento) => {
            setPagina(1)
            setCategoria(evento.target.value as CategoriaGasto | '')
          }}
        >
          <option value="">Todas</option>
          {opcoesDe(CATEGORIAS_GASTO)}
        </CampoSelecao>
      </div>

      {carregando ? <Carregando /> : null}
      {erro ? <Aviso>{erro}</Aviso> : null}

      {dados && !carregando ? (
        dados.itens.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum gasto registrado"
            descricao="Registre as despesas do abrigo para que a prestação de contas mostre para onde foi o dinheiro."
          />
        ) : (
          <>
            <div className="tabela-envolucro">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Gasto</th>
                    <th className="numero">Valor</th>
                    {ehAdmin ? (
                      <th>
                        <span className="so-leitor-tela">Ações</span>
                      </th>
                    ) : null}
                  </tr>
                </thead>
                <tbody>
                  {dados.itens.map((gasto) => (
                    <tr key={gasto.id} data-estorno={gasto.estorno_de_id ? 'sim' : undefined}>
                      <td className="numero-tabular">{formatarData(gasto.data)}</td>
                      <td className="principal">
                        {gasto.descricao}
                        <span className="contato-linha texto-fraco">
                          {CATEGORIAS_GASTO[gasto.categoria]}
                          {gasto.pet_nome ? ` · ${gasto.pet_nome}` : ''} · por{' '}
                          {gasto.registrado_por_nome}
                        </span>
                        <SituacaoDoLancamento lancamento={gasto} />
                      </td>
                      <td className="numero">{formatarMoeda(gasto.valor)}</td>
                      {ehAdmin ? (
                        <td>
                          <EstornarLancamento
                            lancamento={gasto}
                            estornar={(motivo) => api.estornar(gasto.id, motivo)}
                            aoEstornar={() =>
                              concluir('Gasto estornado. O estorno entrou com a data de hoje.')
                            }
                            aoFalhar={(texto) => setMensagem({ tom: 'erro', texto })}
                          />
                        </td>
                      ) : null}
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

      {registrando ? (
        <RegistrarGasto
          aoFechar={() => setRegistrando(false)}
          aoSalvar={() => concluir('Gasto registrado.')}
        />
      ) : null}
    </>
  )
}

/* --- Registro --------------------------------------------------------- */

function RegistrarGasto({ aoFechar, aoSalvar }: { aoFechar: () => void; aoSalvar: () => void }) {
  const listaDePets = useRequisicao(() => apiPets.listar({ tamanho_pagina: 100 }), [])
  const [valor, setValor] = useState('')
  const [data, setData] = useState(dataDeHoje())
  const [categoria, setCategoria] = useState<CategoriaGasto>('alimentacao')
  const [descricao, setDescricao] = useState('')
  const [petId, setPetId] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({})
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setErrosCampo({})
    const numero = Number(valor.replace(',', '.'))
    if (!Number.isFinite(numero) || numero <= 0 || numero > VALOR_MAXIMO) {
      setErrosCampo({ valor: 'Informe um valor entre R$ 0,01 e R$ 99.999.999,99.' })
      return
    }
    setSalvando(true)
    try {
      await api.registrar({
        valor: numero,
        data,
        categoria,
        descricao: descricao.trim(),
        pet_id: petId ? Number(petId) : null,
      })
      aoSalvar()
    } catch (problema) {
      if (problema instanceof ErroApi) {
        setErro(problema.mensagemDeTela())
        setErrosCampo(problema.porCampo)
      } else {
        setErro('Não foi possível registrar o gasto.')
      }
      setSalvando(false)
    }
  }

  return (
    <Sobreposicao titulo="Registrar gasto" aoFechar={aoFechar}>
      <form className="formulario" onSubmit={enviar}>
        {erro ? <Aviso>{erro}</Aviso> : null}
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
            onChange={(e) => setValor(e.target.value)}
          />
          <Campo
            rotulo="Data"
            type="date"
            required
            max={dataDeHoje()}
            value={data}
            erro={errosCampo.data}
            onChange={(e) => setData(e.target.value)}
          />
        </div>
        <CampoSelecao
          rotulo="Categoria"
          value={categoria}
          onChange={(e) => setCategoria(e.target.value as CategoriaGasto)}
        >
          {opcoesDe(CATEGORIAS_GASTO)}
        </CampoSelecao>
        <Campo
          rotulo="Descrição"
          required
          maxLength={500}
          value={descricao}
          erro={errosCampo.descricao}
          dica="Fica só no painel da equipe. O portal público mostra a categoria, nunca a descrição."
          onChange={(e) => setDescricao(e.target.value)}
        />
        <CampoSelecao
          rotulo="Para qual pet"
          value={petId}
          dica="Opcional. Sem pet, o gasto é do abrigo como um todo."
          onChange={(e) => setPetId(e.target.value)}
        >
          <option value="">Gasto geral do abrigo</option>
          {(listaDePets.dados?.itens ?? []).map((pet) => (
            <option key={pet.id} value={pet.id}>
              {pet.nome}
            </option>
          ))}
        </CampoSelecao>
        <div className="acoes">
          <button type="submit" className="botao" disabled={salvando}>
            {salvando ? 'Salvando…' : 'Registrar gasto'}
          </button>
          <button type="button" className="botao" data-tipo="texto" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </form>
    </Sobreposicao>
  )
}
