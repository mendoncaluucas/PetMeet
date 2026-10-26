import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Aviso, Carregando } from './componentes/Interface'
import { Layout } from './componentes/Layout'
import { useAuth } from './auth/ContextoAuth'
import { Login } from './paginas/Login'
import { Painel } from './paginas/Painel'
import { PainelVeterinario } from './paginas/PainelVeterinario'
import { Pets } from './paginas/Pets'
import { PetNovo } from './paginas/PetNovo'
import { PetDetalhe } from './paginas/PetDetalhe'
import { Adocoes } from './paginas/Adocoes'
import { Adotantes } from './paginas/Adotantes'
import { Padrinhos } from './paginas/Padrinhos'
import { Doacoes } from './paginas/Doacoes'
import { Equipe } from './paginas/Equipe'
import { Gastos } from './paginas/Gastos'
import { Transparencia } from './paginas/Transparencia'
import { Vacinas } from './paginas/Vacinas'
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

/**
 * Telas da equipe (admin e voluntario). O veterinario que chegar pela barra de endereco
 * ve um aviso em vez de uma tela cheia de erros 403. Espera o perfil para nao disparar as
 * requisicoes da tela antes da hora; se o /auth/me falhar, a tela abre como antes e quem
 * recusa de verdade e a API.
 */
function SoEquipe({ children }: { children: ReactNode }) {
  const { usuario, perfilFalhou, ehEquipe } = useAuth()

  if (!usuario && !perfilFalhou) return <Carregando texto="Conferindo seu perfil…" />
  if (!ehEquipe) return <Aviso>Seu perfil não tem acesso a esta tela.</Aviso>
  return <>{children}</>
}

/** Pagina inicial: o resumo da equipe traz nomes de adotantes, o do veterinario e clinico. */
function Inicio() {
  const { usuario, perfilFalhou, ehVeterinario } = useAuth()

  // Sem o perfil, o Painel da equipe e o que sempre abriu aqui.
  if (!usuario && !perfilFalhou) return <Carregando texto="Conferindo seu perfil…" />
  return ehVeterinario ? <PainelVeterinario /> : <Painel />
}

export function App() {
  const { autenticado } = useAuth()

  return (
    <Routes>
      <Route path="/entrar" element={autenticado ? <Navigate to="/" replace /> : <Login />} />
      {/* Publica, com ou sem sessao (H11, D4). */}
      <Route path="/transparencia" element={<Transparencia />} />

      <Route
        element={
          <ExigeSessao>
            <Layout />
          </ExigeSessao>
        }
      >
        <Route index element={<Inicio />} />
        <Route path="pets" element={<Pets />} />
        <Route path="pets/:id" element={<PetDetalhe />} />
        {/* Todos os perfis: a equipe consulta, admin e veterinario mantem (D9). */}
        <Route path="vacinas" element={<Vacinas />} />
        <Route
          path="pets/novo"
          element={
            <SoEquipe>
              <PetNovo />
            </SoEquipe>
          }
        />
        <Route
          path="adocoes"
          element={
            <SoEquipe>
              <Adocoes />
            </SoEquipe>
          }
        />
        <Route
          path="adotantes"
          element={
            <SoEquipe>
              <Adotantes />
            </SoEquipe>
          }
        />
        <Route
          path="padrinhos"
          element={
            <SoEquipe>
              <Padrinhos />
            </SoEquipe>
          }
        />
        <Route
          path="doacoes"
          element={
            <SoEquipe>
              <Doacoes />
            </SoEquipe>
          }
        />
        <Route
          path="gastos"
          element={
            <SoEquipe>
              <Gastos />
            </SoEquipe>
          }
        />
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
