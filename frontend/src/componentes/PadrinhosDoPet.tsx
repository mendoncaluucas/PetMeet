/**
 * Padrinhos na ficha do pet (fase 3, H7.6). A equipe ve quem apadrinha e quanto; o
 * veterinario, que nao ve a parte financeira (D14), so a contagem.
 */

import { Link } from 'react-router-dom'
import { apadrinhamentos, pets } from '../api/recursos'
import { Aviso, Carregando } from './Interface'
import { contagem, formatarData, formatarMoeda } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

interface Props {
  petId: number
  mostrarNomes: boolean
}

export function PadrinhosDoPet({ petId, mostrarNomes }: Props) {
  return (
    <section className="ficha">
      <div className="ficha-corpo pilha-3">
        <div className="secao-titulo">
          <h2>Padrinhos</h2>
          {mostrarNomes ? (
            <Link to="/padrinhos" className="texto-fraco">
              Ver padrinhos
            </Link>
          ) : null}
        </div>
        {mostrarNomes ? <ListaDaEquipe petId={petId} /> : <SoContagem petId={petId} />}
      </div>
    </section>
  )
}

function SoContagem({ petId }: { petId: number }) {
  const { dados, carregando, erro } = useRequisicao(() => pets.padrinhos(petId), [petId])

  if (carregando) return <Carregando texto="Contando os padrinhos…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!dados) return null
  return (
    <p>
      {dados.ativos === 0
        ? 'Nenhum padrinho no momento.'
        : `${contagem(dados.ativos, 'padrinho ativo', 'padrinhos ativos')}.`}
    </p>
  )
}

function ListaDaEquipe({ petId }: { petId: number }) {
  const { dados, carregando, erro } = useRequisicao(
    () => apadrinhamentos.listar({ pet_id: petId, tamanho_pagina: 100 }),
    [petId],
  )

  if (carregando) return <Carregando texto="Buscando os padrinhos…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!dados || dados.itens.length === 0) {
    return (
      <p className="texto-fraco">
        Nenhum padrinho no momento. O apadrinhamento é registrado na tela de padrinhos.
      </p>
    )
  }

  const total = dados.itens.reduce((soma, item) => soma + Number(item.valor_mensal), 0)
  return (
    <>
      <p>
        {contagem(dados.total, 'padrinho ativo', 'padrinhos ativos')}, somando{' '}
        <strong className="numero-tabular">{formatarMoeda(total)}</strong> por mês.
      </p>
      <div className="lista-atencao">
        {dados.itens.map((item) => (
          <div key={item.id} className="item-atencao">
            <span>
              <span className="item-atencao-nome">{item.padrinho_nome}</span>
              <span className="item-atencao-detalhe">desde {formatarData(item.data_inicio)}</span>
            </span>
            <span className="item-atencao-fim numero-tabular">
              {formatarMoeda(item.valor_mensal)}/mês
            </span>
          </div>
        ))}
      </div>
    </>
  )
}
