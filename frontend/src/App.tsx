import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Aviso, Carregando } from './componentes/Interface'
import { Layout } from './componentes/Layout'
import { useAuth } from './auth/ContextoAuth'
import { Login } from './paginas/Login'
import { Painel } from './paginas/Painel'
import { Pets } from './paginas/Pets'
import { PetNovo } from './paginas/PetNovo'
import { PetDetalhe } from './paginas/PetDetalhe'
import { Adocoes } from './paginas/Adocoes'
import { Adotantes } from './paginas/Adotantes'
import { Padrinhos } from './paginas/Padrinhos'
import { Doacoes } from './paginas/Doacoes'
import { Equipe } from './paginas/Equipe'
import { NaoEncontrada } from './paginas/NaoEncontrada'

function ExigeSessao({ children }: { children: ReactNode }) {
  const { autenticado } = useAuth()
  const local = useLocation()

  // Guarda onde a pessoa queria chegar para devolve-la ao lugar certo depois.
  if (!autenticado) return <Navigate to="/entrar" replace state={{ destino: local.pathname }} />
  return <>{children}</>
}

/** Tela so de admin. Enquanto o perfil nao chegou, espera em vez de recusar. */
function ExigeAdmin({ children }: { children: ReactNode }) {
  const { usuario, perfilFalhou, ehAdmin } = useAuth()

  if (!usuario && perfilFalhou) {
    return <Aviso>Não foi possível conferir seu perfil agora. Recarregue a página.</Aviso>
  }
  if (!usuario) return <Carregando texto="Conferindo seu perfil…" />
  if (!ehAdmin) return <Aviso>Só administradores gerenciam a equipe.</Aviso>
  return <>{children}</>
}

export function App() {
  const { autenticado } = useAuth()

  return (
    <Routes>
      <Route path="/entrar" element={autenticado ? <Navigate to="/" replace /> : <Login />} />

      <Route
        element={
          <ExigeSessao>
            <Layout />
          </ExigeSessao>
        }
      >
        <Route index element={<Painel />} />
        <Route path="pets" element={<Pets />} />
        <Route path="pets/novo" element={<PetNovo />} />
        <Route path="pets/:id" element={<PetDetalhe />} />
        <Route path="adocoes" element={<Adocoes />} />
        <Route path="adotantes" element={<Adotantes />} />
        <Route path="padrinhos" element={<Padrinhos />} />
        <Route path="doacoes" element={<Doacoes />} />
        <Route
          path="equipe"
          element={
            <ExigeAdmin>
              <Equipe />
            </ExigeAdmin>
          }
        />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  )
}
