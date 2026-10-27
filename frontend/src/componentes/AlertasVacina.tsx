/**
 * Quadro "Vacinas" das paginas iniciais (fase 2, H6): vencidas e vencendo em ate 30 dias,
 * das mais atrasadas primeiro. Cada alerta abre o cartao de vacinacao do pet.
 *
 * Busca a parte do resumo do Painel: se os alertas falharem, so este quadro avisa.
 */

import { Link } from 'react-router-dom'
import { vacinacao } from '../api/recursos'
import { Aviso, Carregando, EstadoVazio, Selo } from './Interface'
import { STATUS_VACINA, TOM_VACINA, contagem, prazoDaDose } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

export function AlertasVacina({ limite }: { limite: number }) {
  const { dados, carregando, erro } = useRequisicao(() => vacinacao.alertas(limite), [limite])

  return (
    <section>
      <div className="secao-titulo">
        <h2>Vacinas</h2>
        {dados ? (
          <span className="texto-fraco">
            {contagem(dados.total_vencidas, 'vencida', 'vencidas')} ·{' '}
            {contagem(dados.total_vencendo, 'vencendo', 'vencendo')} em 30 dias
          </span>
        ) : null}
      </div>

      {carregando ? (
        <Carregando texto="Conferindo os cartões de vacinação…" />
      ) : erro ? (
        <Aviso>{erro}</Aviso>
      ) : !dados || dados.itens.length === 0 ? (
        <EstadoVazio
          titulo="Nenhuma vacina vencida ou vencendo"
          descricao="Quando a próxima dose de uma vacina estiver a 30 dias ou menos, o pet aparece aqui."
        />
      ) : (
        <>
          <div className="lista-atencao">
            {dados.itens.map((alerta) => (
              <Link
                key={`${alerta.pet_id}-${alerta.vacina_id}`}
                to={`/pets/${alerta.pet_id}#cartao-vacinacao`}
                className="item-atencao"
                data-vacina={alerta.status}
              >
                <span>
                  <span className="item-atencao-nome">{alerta.pet_nome}</span>
                  <span className="item-atencao-detalhe">
                    {alerta.vacina_nome} · {prazoDaDose(alerta.dias_para_vencer)}
                  </span>
                </span>
                <span className="item-atencao-fim">
                  <Selo tom={TOM_VACINA[alerta.status]}>{STATUS_VACINA[alerta.status]}</Selo>
                </span>
              </Link>
            ))}
          </div>
          {dados.total_vencidas + dados.total_vencendo > dados.itens.length ? (
            <p className="texto-fraco">
              Mostrando os {dados.itens.length} mais urgentes de{' '}
              {dados.total_vencidas + dados.total_vencendo}.
            </p>
          ) : null}
        </>
      )}
    </section>
  )
}
