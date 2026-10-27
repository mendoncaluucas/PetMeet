/** Campos de formulario com rotulo, dica e mensagem de erro por campo. */

import { useId } from 'react'
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

interface Comum {
  rotulo: string
  dica?: string
  erro?: string
}

type CampoProps = Comum & InputHTMLAttributes<HTMLInputElement>

export function Campo({ rotulo, dica, erro, ...resto }: CampoProps) {
  const id = useId()
  const idDica = `${id}-dica`
  const idErro = `${id}-erro`

  return (
    <div className="campo" data-invalido={erro ? 'sim' : undefined}>
      <label htmlFor={id}>{rotulo}</label>
      <input
        id={id}
        aria-invalid={erro ? true : undefined}
        aria-describedby={
          [dica ? idDica : null, erro ? idErro : null].filter(Boolean).join(' ') || undefined
        }
        {...resto}
      />
      {dica ? (
        <span className="campo-dica" id={idDica}>
          {dica}
        </span>
      ) : null}
      {erro ? (
        <span className="campo-erro" id={idErro}>
          {erro}
        </span>
      ) : null}
    </div>
  )
}

type CampoTextoProps = Comum & TextareaHTMLAttributes<HTMLTextAreaElement>

/** Texto longo (anamnese, conduta): mesmo rotulo, dica e erro do Campo. */
export function CampoTexto({ rotulo, dica, erro, ...resto }: CampoTextoProps) {
  const id = useId()
  const idDica = `${id}-dica`
  const idErro = `${id}-erro`

  return (
    <div className="campo" data-invalido={erro ? 'sim' : undefined}>
      <label htmlFor={id}>{rotulo}</label>
      <textarea
        id={id}
        rows={4}
        aria-invalid={erro ? true : undefined}
        aria-describedby={
          [dica ? idDica : null, erro ? idErro : null].filter(Boolean).join(' ') || undefined
        }
        {...resto}
      />
      {dica ? (
        <span className="campo-dica" id={idDica}>
          {dica}
        </span>
      ) : null}
      {erro ? (
        <span className="campo-erro" id={idErro}>
          {erro}
        </span>
      ) : null}
    </div>
  )
}

type CampoSelecaoProps = Comum & SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }

export function CampoSelecao({ rotulo, dica, erro, children, ...resto }: CampoSelecaoProps) {
  const id = useId()
  const idErro = `${id}-erro`

  return (
    <div className="campo" data-invalido={erro ? 'sim' : undefined}>
      <label htmlFor={id}>{rotulo}</label>
      <select
        id={id}
        aria-invalid={erro ? true : undefined}
        aria-describedby={erro ? idErro : undefined}
        {...resto}
      >
        {children}
      </select>
      {dica ? <span className="campo-dica">{dica}</span> : null}
      {erro ? (
        <span className="campo-erro" id={idErro}>
          {erro}
        </span>
      ) : null}
    </div>
  )
}

interface CampoMarcadorProps extends InputHTMLAttributes<HTMLInputElement> {
  rotulo: string
  dica?: string
}

export function CampoMarcador({ rotulo, dica, ...resto }: CampoMarcadorProps) {
  return (
    <label className="campo-marcador">
      <input type="checkbox" {...resto} />
      <span>
        {rotulo}
        {dica ? <small>{dica}</small> : null}
      </span>
    </label>
  )
}

/** Monta as opcoes de um select a partir dos dicionarios de rotulos. */
// eslint-disable-next-line react-refresh/only-export-components
export function opcoesDe<T extends string>(mapa: Record<T, string>) {
  return (Object.entries(mapa) as [T, string][]).map(([valor, rotulo]) => (
    <option key={valor} value={valor}>
      {rotulo}
    </option>
  ))
}
