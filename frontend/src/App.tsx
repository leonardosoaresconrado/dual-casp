import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { ScopeProvider } from "./scope/ScopeContext";
import { ParametrosProvider } from "./parametros/ParametrosContext";
import { DashboardLayout } from "./layout/DashboardLayout";
import { LoginPage } from "./pages/LoginPage";
import { ExecucaoOrcamentariaPage } from "./pages/ExecucaoOrcamentariaPage";
import { RelatorioLOAPage } from "./pages/RelatorioLOAPage";
import { RelatorioExecucaoPage } from "./pages/RelatorioExecucaoPage";
import { RelatorioReceitaPage } from "./pages/RelatorioReceitaPage";
import { ReceitaPage } from "./pages/ReceitaPage";
import { EmDesenvolvimentoPage } from "./pages/EmDesenvolvimentoPage";
import { RestosAPagarPage } from "./pages/RestosAPagarPage";
import { RestosAPagarGraficosPage } from "./pages/RestosAPagarGraficosPage";
import { SaldoBalancoPage } from "./pages/SaldoBalancoPage";
import { SaldoContaBancariaPage } from "./pages/SaldoContaBancariaPage";
import { RelatorioFinanceiroPage } from "./pages/RelatorioFinanceiroPage";
import { RelatorioFinanceiroGraficosPage } from "./pages/RelatorioFinanceiroGraficosPage";
import { ExecucaoFiscalPage } from "./pages/ExecucaoFiscalPage";
import { ExecucaoFiscalDetalhadoPage } from "./pages/ExecucaoFiscalDetalhadoPage";
import { ResumoGeralFiscalPage } from "./pages/ResumoGeralFiscalPage";
import { LOAPage } from "./pages/cadastros/LOAPage";
import { RubricasReceitaPage } from "./pages/cadastros/RubricasReceitaPage";
import { RubricasDespesaPage } from "./pages/cadastros/RubricasDespesaPage";
import { MunicipiosPage } from "./pages/cadastros/MunicipiosPage";
import { UnidadesGestorasPage } from "./pages/cadastros/UnidadesGestorasPage";
import { UsuariosPage } from "./pages/cadastros/UsuariosPage";
import { ImportacoesPage } from "./pages/cadastros/ImportacoesPage";
import { ParametrosPage } from "./pages/cadastros/ParametrosPage";
import { ClassificacaoReceitaOrigensPage } from "./pages/cadastros/ClassificacaoReceitaOrigensPage";
import { ClassificacaoReceitaEspeciesPage } from "./pages/cadastros/ClassificacaoReceitaEspeciesPage";
import { ClassificacaoReceitaRubricasPage } from "./pages/cadastros/ClassificacaoReceitaRubricasPage";
import { ClassificacaoReceitaAlineasPage } from "./pages/cadastros/ClassificacaoReceitaAlineasPage";
import { ClassificacaoReceitaSubalineasPage } from "./pages/cadastros/ClassificacaoReceitaSubalineasPage";
import { ClassificacaoReceitaTiposPage } from "./pages/cadastros/ClassificacaoReceitaTiposPage";
import { ExerciciosPage } from "./pages/cadastros/ExerciciosPage";
import { EstruturaOrganizacionalPage } from "./pages/cadastros/EstruturaOrganizacionalPage";
import { FuncoesPage } from "./pages/cadastros/FuncoesPage";
import { SubfuncoesPage } from "./pages/cadastros/SubfuncoesPage";
import { ProgramasPage } from "./pages/cadastros/ProgramasPage";
import { AcoesPage } from "./pages/cadastros/AcoesPage";
import { CategoriasEconomicasPage } from "./pages/cadastros/CategoriasEconomicasPage";
import { GruposNaturezaDespesaPage } from "./pages/cadastros/GruposNaturezaDespesaPage";
import { ModalidadesAplicacaoPage } from "./pages/cadastros/ModalidadesAplicacaoPage";
import { ElementosDespesaPage } from "./pages/cadastros/ElementosDespesaPage";
import { SubelementosPage } from "./pages/cadastros/SubelementosPage";
import { FontesRecursosPage } from "./pages/cadastros/FontesRecursosPage";
import { ObrigacoesPage } from "./pages/ObrigacoesPage";
import { TiposObrigacaoPage } from "./pages/cadastros/TiposObrigacaoPage";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <ScopeProvider>
              <DashboardLayout>
                <Routes>
                  <Route path="/" element={<Navigate to="/execucao-orcamentaria" replace />} />
                  <Route path="/execucao-orcamentaria" element={<ExecucaoOrcamentariaPage />} />
                  <Route path="/relatorio-loa" element={<RelatorioLOAPage />} />
                  <Route path="/relatorio-execucao" element={<RelatorioExecucaoPage />} />
                  <Route path="/receita" element={<ReceitaPage />} />
                  <Route path="/orcamento/ppa" element={<EmDesenvolvimentoPage titulo="PPA - Plano Plurianual" />} />
                  <Route path="/orcamento/ldo" element={<EmDesenvolvimentoPage titulo="LDO - Lei de Diretrizes Orçamentárias" />} />
                  <Route path="/orcamento/loa/despesas/rubricas" element={<RubricasDespesaPage />} />
                  <Route path="/orcamento/loa/receitas" element={<RubricasReceitaPage />} />
                  <Route path="/orcamento/loa/receitas/origens" element={<ClassificacaoReceitaOrigensPage />} />
                  <Route path="/orcamento/loa/receitas/especies" element={<ClassificacaoReceitaEspeciesPage />} />
                  <Route path="/orcamento/loa/receitas/rubricas-stn" element={<ClassificacaoReceitaRubricasPage />} />
                  <Route path="/orcamento/loa/receitas/alineas" element={<ClassificacaoReceitaAlineasPage />} />
                  <Route path="/orcamento/loa/receitas/subalineas" element={<ClassificacaoReceitaSubalineasPage />} />
                  <Route path="/orcamento/loa/receitas/tipos" element={<ClassificacaoReceitaTiposPage />} />
                  <Route path="/financeiro/saldo-balanco" element={<SaldoBalancoPage />} />
                  <Route path="/financeiro/saldo-conta" element={<SaldoContaBancariaPage />} />
                  <Route path="/financeiro/restos-a-pagar" element={<RestosAPagarPage />} />
                  <Route path="/relatorios/receitas" element={<RelatorioReceitaPage />} />
                  <Route path="/relatorios/financeiro" element={<RelatorioFinanceiroPage />} />
                  <Route path="/relatorios/financeiro/graficos" element={<RelatorioFinanceiroGraficosPage />} />
                  <Route path="/execucao-fiscal" element={<ExecucaoFiscalPage />} />
                  <Route path="/execucao-fiscal/detalhado" element={<ExecucaoFiscalDetalhadoPage />} />
                  <Route path="/execucao-fiscal/resumo" element={<ResumoGeralFiscalPage />} />
                  <Route path="/obrigacoes" element={<ObrigacoesPage />} />
                  <Route path="/admin/tipos-obrigacao" element={<TiposObrigacaoPage />} />
                  <Route path="/relatorios/restos-a-pagar" element={<RestosAPagarPage />} />
                  <Route path="/relatorios/restos-a-pagar/graficos" element={<RestosAPagarGraficosPage />} />
                  <Route path="/cadastros/loa" element={<LOAPage />} />
                  <Route path="/cadastros/exercicios" element={<ExerciciosPage />} />
                  <Route path="/cadastros/estrutura-organizacional" element={<EstruturaOrganizacionalPage />} />
                  <Route path="/cadastros/orgaos" element={<Navigate to="/cadastros/estrutura-organizacional" replace />} />
                  <Route path="/cadastros/unidades-orcamentarias" element={<Navigate to="/cadastros/estrutura-organizacional" replace />} />
                  <Route path="/cadastros/funcoes" element={<FuncoesPage />} />
                  <Route path="/cadastros/subfuncoes" element={<SubfuncoesPage />} />
                  <Route path="/cadastros/programas" element={<ProgramasPage />} />
                  <Route path="/cadastros/acoes" element={<AcoesPage />} />
                  <Route path="/cadastros/categorias-economicas" element={<CategoriasEconomicasPage />} />
                  <Route path="/cadastros/grupos-natureza-despesa" element={<GruposNaturezaDespesaPage />} />
                  <Route path="/cadastros/modalidades-aplicacao" element={<ModalidadesAplicacaoPage />} />
                  <Route path="/cadastros/elementos-despesa" element={<ElementosDespesaPage />} />
                  <Route path="/cadastros/subelementos" element={<SubelementosPage />} />
                  <Route path="/cadastros/fontes-recursos" element={<FontesRecursosPage />} />
                  <Route path="/admin/municipios" element={<MunicipiosPage />} />
                  <Route path="/admin/unidades-gestoras" element={<UnidadesGestorasPage />} />
                  <Route path="/admin/usuarios" element={<UsuariosPage />} />
                  <Route path="/admin/importacoes" element={<ImportacoesPage />} />
                  <Route path="/admin/parametros" element={<ParametrosPage />} />
                </Routes>
              </DashboardLayout>
            </ScopeProvider>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ParametrosProvider>
        <AppRoutes />
      </ParametrosProvider>
    </AuthProvider>
  );
}
