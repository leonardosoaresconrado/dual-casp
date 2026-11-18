import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  InputAdornment,
  MenuItem,
  Paper,
  Select,
  Switch,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  IconButton,
  Button,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import EditIcon from "@mui/icons-material/Edit";
import { api, buscarTodasPaginas } from "../api/client";
import type {
  ApuracaoASPS,
  ApuracaoDTP,
  ApuracaoETIFundeb,
  ApuracaoMagisterioFundeb,
  ApuracaoMDE,
  ApuracaoReprogramacaoFundeb,
  ApuracaoVAATDespesaCapital,
  ApuracaoVAATEducacaoInfantil,
  ApuracaoValorNaoAplicadoFundeb,
  Exercicio,
  LancamentoExecucaoOrcamentaria,
} from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { CAMPOS_MDE } from "./camposApuracaoMDE";

const BIMESTRES = [1, 2, 3, 4, 5, 6];

function formatarMoeda(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// Formata um valor decimal cru (ex. "33691133.37") com separador de milhar
// e vírgula decimal pt-BR (ex. "33.691.133,37") — usado só pra EXIBIR o
// valor no diálogo do 6º bimestre quando o campo não está focado.
function formatarValorEntrada(valor: string): string {
  const n = Number(valor);
  if (Number.isNaN(n)) return valor;
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Converte o texto que o usuário digita (pt-BR "33.691.133,37" ou já cru
// "33691133.37") de volta pro decimal cru que a API espera — remove pontos
// de milhar e troca a vírgula decimal por ponto.
function normalizarValorEntrada(texto: string): string {
  return texto.replace(/\./g, "").replace(",", ".").replace(/[^\d.-]/g, "");
}

function formatarPercentual(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return `${Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

// Análise horizontal clássica: variação de uma linha entre o bimestre
// atual e o imediatamente anterior. Linhas monetárias ("moeda") usam
// variação percentual relativa (`anterior = 0` não tem variação % que
// faça sentido matemático, por isso retorna null nesse caso em vez de
// Infinity/NaN). Linhas que JÁ são percentuais (os índices — ÍNDICE STN,
// ÍNDICE GERENCIAL etc.) usam a diferença em PONTOS PERCENTUAIS (p.p.,
// simples subtração) — variação relativa de um percentual (ex. 24%→26%
// como "+8,3%") é tecnicamente correta mas confunde mais do que ajuda
// numa taxa/índice; p.p. é o padrão usado em relatórios fiscais reais.
function calcularVariacao(
  atual: string | number | null | undefined,
  anterior: string | number | null | undefined,
  tipo: "moeda" | "percentual"
): number | null {
  if (atual === null || atual === undefined || anterior === null || anterior === undefined) return null;
  const a = Number(atual);
  const b = Number(anterior);
  if (tipo === "percentual") return a - b;
  if (b === 0) return null;
  return ((a - b) / Math.abs(b)) * 100;
}

// "valores" = só o valor (padrão); "valores_variacao" = valor + variação
// anotada abaixo (não esconde nada); "crescimento" = o valor some, só o
// crescimento entre bimestres aparece (nominal R$ + % pra linhas
// monetárias, só p.p. pra linhas de índice, já que não existe um
// "nominal" separado pra um percentual).
type ModoExibicao = "valores" | "valores_variacao" | "crescimento";

interface LinhaPivot<T> {
  chave: string;
  rotulo: string;
  tipo: "moeda" | "percentual" | "texto";
  negrito?: boolean;
  destaque?: boolean;
  cor?: "error";
  valor: (d: T) => string | number | null | undefined;
  filhos?: LinhaPivot<T>[];
}

function TabelaPivot<T>({
  linhas,
  dadosPorBimestre,
  modo,
  colunaProjetada,
}: {
  linhas: LinhaPivot<T>[];
  dadosPorBimestre: Record<number, T>;
  modo: ModoExibicao;
  // Bimestre cujo valor em `dadosPorBimestre` é uma projeção sintética
  // (não um dado real importado) — só marca visualmente (itálico + rótulo
  // "(projetado)" no cabeçalho), não muda nenhum cálculo desta tabela.
  colunaProjetada?: number;
}) {
  const [abertos, setAbertos] = useState<Record<string, boolean>>({});

  function toggle(chave: string) {
    setAbertos((a) => ({ ...a, [chave]: !a[chave] }));
  }

  function renderLinha(linha: LinhaPivot<T>, nivel: number): React.ReactNode[] {
    const aberto = abertos[linha.chave] ?? false;
    const linha_jsx = (
      <TableRow key={linha.chave} sx={linha.destaque ? { backgroundColor: "action.hover" } : undefined}>
        <TableCell sx={{ pl: 2 + nivel * 2.5, fontWeight: linha.negrito ? 700 : 400, whiteSpace: "nowrap" }}>
          {linha.filhos ? (
            <IconButton size="small" onClick={() => toggle(linha.chave)} sx={{ mr: 0.5 }}>
              {aberto ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          ) : null}
          {linha.rotulo}
        </TableCell>
        {BIMESTRES.map((b, idx) => {
          const d = dadosPorBimestre[b];
          const valor = d ? linha.valor(d) : null;
          const bimestreAnterior = BIMESTRES[idx - 1];
          const dAnterior = bimestreAnterior ? dadosPorBimestre[bimestreAnterior] : undefined;
          const valorAnterior = dAnterior ? linha.valor(dAnterior) : null;
          const ehTexto = linha.tipo === "texto";
          const mostrarVariacao = modo !== "valores" && !ehTexto;
          const variacao = mostrarVariacao
            ? calcularVariacao(valor, valorAnterior, linha.tipo === "percentual" ? "percentual" : "moeda")
            : null;
          const esconderValorBase = modo === "crescimento" && !ehTexto;
          const sufixoVariacao = linha.tipo === "percentual" ? "p.p." : "%";
          const deltaNominal =
            modo === "crescimento" && linha.tipo === "moeda" && valor != null && valorAnterior != null
              ? Number(valor) - Number(valorAnterior)
              : null;

          return (
            <TableCell
              key={b}
              align="right"
              sx={{
                color: linha.cor === "error" ? "error.main" : undefined,
                fontWeight: linha.negrito ? 700 : 400,
                fontStyle: colunaProjetada === b ? "italic" : undefined,
                opacity: colunaProjetada === b ? 0.75 : undefined,
              }}
            >
              {!esconderValorBase &&
                (linha.tipo === "percentual"
                  ? formatarPercentual(valor)
                  : linha.tipo === "texto"
                  ? valor || "—"
                  : formatarMoeda(valor))}
              {deltaNominal !== null && <Box>{formatarMoeda(deltaNominal)}</Box>}
              {modo === "crescimento" && !ehTexto && variacao === null && (
                <Typography component="div" variant="caption" color="text.secondary">—</Typography>
              )}
              {variacao !== null && (
                <Typography
                  component="div"
                  variant="caption"
                  sx={{ color: variacao >= 0 ? "success.main" : "error.main", fontWeight: 400 }}
                >
                  {variacao >= 0 ? "▲" : "▼"}{" "}
                  {Math.abs(variacao).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}{" "}
                  {sufixoVariacao}
                </Typography>
              )}
            </TableCell>
          );
        })}
      </TableRow>
    );
    const resultado: React.ReactNode[] = [linha_jsx];
    if (linha.filhos && aberto) {
      for (const filho of linha.filhos) {
        resultado.push(...renderLinha(filho, nivel + 1));
      }
    }
    return resultado;
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Item</TableCell>
            {BIMESTRES.map((b) => (
              <TableCell key={b} align="right" sx={{ fontStyle: colunaProjetada === b ? "italic" : undefined }}>
                {b}º Bimestre
                {colunaProjetada === b && (
                  <Typography component="div" variant="caption" color="text.secondary">
                    (projetado)
                  </Typography>
                )}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {dadosPorBimestre && Object.keys(dadosPorBimestre).length === 0 ? (
            <TableRow>
              <TableCell colSpan={BIMESTRES.length + 1} align="center">
                Nenhum dado importado para este exercício.
              </TableCell>
            </TableRow>
          ) : (
            linhas.flatMap((l) => renderLinha(l, 0))
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function linhasDTP(): LinhaPivot<ApuracaoDTP>[] {
  return [
    { chave: "rcl", rotulo: "(+) Receita Corrente Líquida", tipo: "moeda", valor: (d) => d.rcl },
    { chave: "ded_ind", rotulo: "(-) Emendas Individuais", tipo: "moeda", valor: (d) => d.deducao_emendas_individuais },
    { chave: "ded_banc", rotulo: "(-) Emendas de Bancada", tipo: "moeda", valor: (d) => d.deducao_emendas_bancada },
    { chave: "ded_acs", rotulo: "(-) Agentes Comunitários de Saúde", tipo: "moeda", valor: (d) => d.deducao_agentes_saude },
    { chave: "ded_outras", rotulo: "(-) Outras Deduções", tipo: "moeda", valor: (d) => d.deducao_outras },
    {
      chave: "rcl_ajustada",
      rotulo: "(=) Receita Corrente Líquida Ajustada",
      tipo: "moeda",
      negrito: true,
      valor: (d) => d.rcl_ajustada,
    },
    { chave: "dtp", rotulo: "(+) Despesa Total com Pessoal", tipo: "moeda", valor: (d) => d.despesa_total_pessoal },
    {
      chave: "pct_dtp",
      rotulo: "(%) ÍNDICE STN",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_dtp,
    },
    { chave: "lim_max", rotulo: "Limite Máximo (54%)", tipo: "moeda", valor: (d) => d.limite_maximo_valor },
    { chave: "lim_prud", rotulo: "Limite Prudencial (51,3%)", tipo: "moeda", valor: (d) => d.limite_prudencial_valor },
    { chave: "lim_alerta", rotulo: "Limite de Alerta (48,6%)", tipo: "moeda", valor: (d) => d.limite_alerta_valor },
  ];
}

// itens_receita agora é uma lista (tabela filha ApuracaoMDEReceitaItem,
// ver backend) em vez de 11 campos flat — procura pelo código do
// sub-item em vez de acessar a propriedade direto.
function itemReceitaMDE(d: ApuracaoMDE, codigo: string): string | undefined {
  return d.itens_receita.find((i) => i.codigo === codigo)?.valor;
}

function linhasMDE(desconsiderarPnae: boolean): LinhaPivot<ApuracaoMDE>[] {
  return [
    {
      chave: "receita_impostos",
      rotulo: "1 - Receitas de Impostos",
      tipo: "moeda",
      negrito: true,
      valor: (d) => d.receita_impostos,
      filhos: [
        { chave: "1.1", rotulo: "1.1 - IPTU", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "1.1") },
        { chave: "1.2", rotulo: "1.2 - ITBI", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "1.2") },
        { chave: "1.3", rotulo: "1.3 - ISS", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "1.3") },
        { chave: "1.4", rotulo: "1.4 - IRRF", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "1.4") },
      ],
    },
    {
      chave: "receita_transferencias",
      rotulo: "2 - Receita de Transferências",
      tipo: "moeda",
      negrito: true,
      valor: (d) => d.receita_transferencias,
      filhos: [
        { chave: "2.1", rotulo: "2.1 - FPM", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "2.1") },
        { chave: "2.2", rotulo: "2.2 - ICMS", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "2.2") },
        { chave: "2.3", rotulo: "2.3 - IPI", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "2.3") },
        { chave: "2.4", rotulo: "2.4 - ITR", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "2.4") },
        { chave: "2.5", rotulo: "2.5 - IPVA", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "2.5") },
        { chave: "2.6", rotulo: "2.6 - IOF", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "2.6") },
        { chave: "2.7", rotulo: "2.7 - Compensações", tipo: "moeda", valor: (d) => itemReceitaMDE(d, "2.7") },
      ],
    },
    { chave: "base_calculo", rotulo: "Base de Cálculo", tipo: "moeda", negrito: true, valor: (d) => d.base_calculo },
    {
      chave: "minimo",
      rotulo: "Mínimo Constitucional (25%)",
      tipo: "moeda",
      valor: (d) => d.minimo_constitucional,
    },
    { chave: "mde_emp", rotulo: "(+) MDE Empenhado", tipo: "moeda", valor: (d) => d.despesa_mde_empenhada },
    { chave: "mde_liq", rotulo: "(+) MDE Liquidado", tipo: "moeda", valor: (d) => d.despesa_mde_liquidada },
    { chave: "mde_pago", rotulo: "(+) MDE Pago", tipo: "moeda", valor: (d) => d.despesa_mde_paga },
    { chave: "fundeb", rotulo: "(+) FUNDEB Transferido", tipo: "moeda", valor: (d) => d.fundeb_transferido },
    {
      chave: "excedente",
      rotulo: "(-) Excedente FUNDEB Não Aplicado",
      tipo: "moeda",
      cor: "error",
      valor: (d) => d.excedente_fundeb_nao_aplicado,
    },
    {
      chave: "cancelamento",
      rotulo: "(-) Cancelamento de RP",
      tipo: "moeda",
      cor: "error",
      valor: (d) => d.cancelamento_rp,
    },
    {
      chave: "aplicacao_pnae",
      rotulo: "(-) Aplicação no PNAE/PEAE de Recursos Próprios",
      tipo: "moeda",
      cor: "error",
      valor: (d) => d.aplicacao_pnae_recursos_proprios,
    },
    {
      chave: "despesa_362_364",
      rotulo: "(-) Despesa com Ensino Médio/Superior (362/364) em Recursos Próprios",
      tipo: "moeda",
      cor: "error",
      valor: (d) => d.despesa_ensino_medio_superior_recursos_proprios,
    },
    { chave: "total_stn", rotulo: "TOTAL STN", tipo: "moeda", negrito: true, valor: (d) => d.valor_aplicado },
    {
      chave: "total_ger_1",
      rotulo: `TOTAL GERENCIAL 1 (Liquidada)${desconsiderarPnae ? " — desconsiderando PNAE/362/364" : ""}`,
      tipo: "moeda",
      valor: (d) => (desconsiderarPnae ? d.total_gerencial_1_desconsiderando_pnae : d.total_gerencial_1),
    },
    {
      chave: "total_ger_2",
      rotulo: `TOTAL GERENCIAL 2 (Empenhada)${desconsiderarPnae ? " — desconsiderando PNAE/362/364" : ""}`,
      tipo: "moeda",
      valor: (d) => (desconsiderarPnae ? d.total_gerencial_2_desconsiderando_pnae : d.total_gerencial_2),
    },
    {
      chave: "total_ger_3",
      rotulo: `TOTAL GERENCIAL 3 (Paga)${desconsiderarPnae ? " — desconsiderando PNAE/362/364" : ""}`,
      tipo: "moeda",
      valor: (d) => (desconsiderarPnae ? d.total_gerencial_3_desconsiderando_pnae : d.total_gerencial_3),
    },
    {
      chave: "indice_stn",
      rotulo: "ÍNDICE STN",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_aplicado,
    },
    {
      chave: "indice_ger_1",
      rotulo: `ÍNDICE GERENCIAL 1 (Liquidada)${desconsiderarPnae ? " — desconsiderando PNAE/362/364" : ""}`,
      tipo: "percentual",
      destaque: true,
      valor: (d) => (desconsiderarPnae ? d.indice_gerencial_1_desconsiderando_pnae : d.indice_gerencial_1),
    },
    {
      chave: "indice_ger_2",
      rotulo: `ÍNDICE GERENCIAL 2 (Empenhada)${desconsiderarPnae ? " — desconsiderando PNAE/362/364" : ""}`,
      tipo: "percentual",
      destaque: true,
      valor: (d) => (desconsiderarPnae ? d.indice_gerencial_2_desconsiderando_pnae : d.indice_gerencial_2),
    },
    {
      chave: "indice_ger_3",
      rotulo: `ÍNDICE GERENCIAL 3 (Paga)${desconsiderarPnae ? " — desconsiderando PNAE/362/364" : ""}`,
      tipo: "percentual",
      destaque: true,
      valor: (d) => (desconsiderarPnae ? d.indice_gerencial_3_desconsiderando_pnae : d.indice_gerencial_3),
    },
  ];
}

function linhasMagisterio(): LinhaPivot<ApuracaoMagisterioFundeb>[] {
  return [
    { chave: "fundeb_total", rotulo: "Receita Total FUNDEB", tipo: "moeda", valor: (d) => d.fundeb_receita_total },
    { chave: "exigido", rotulo: "Mínimo Constitucional (70%)", tipo: "moeda", valor: (d) => d.valor_exigido },
    { chave: "aplicado", rotulo: "Valor Aplicado", tipo: "moeda", negrito: true, valor: (d) => d.valor_aplicado },
    {
      chave: "indice",
      rotulo: "ÍNDICE STN",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_aplicado,
    },
  ];
}

function linhasETIFundeb(): LinhaPivot<ApuracaoETIFundeb>[] {
  return [
    { chave: "fundeb_total", rotulo: "Receita Total FUNDEB", tipo: "moeda", valor: (d) => d.fundeb_receita_total },
    { chave: "exigido", rotulo: "Mínimo Constitucional (4%)", tipo: "moeda", valor: (d) => d.valor_exigido },
    { chave: "aplicado", rotulo: "Valor Aplicado", tipo: "moeda", negrito: true, valor: (d) => d.valor_aplicado },
    {
      chave: "indice",
      rotulo: "ÍNDICE STN",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_aplicado,
    },
  ];
}

function linhasASPS(): LinhaPivot<ApuracaoASPS>[] {
  return [
    {
      chave: "receita",
      rotulo: "Receita de Impostos/Transferências",
      tipo: "moeda",
      valor: (d) => d.receita_impostos_transferencias,
    },
    { chave: "base_calculo", rotulo: "Base de Cálculo", tipo: "moeda", negrito: true, valor: (d) => d.base_calculo },
    {
      chave: "minimo",
      rotulo: "Mínimo Constitucional (15%)",
      tipo: "moeda",
      valor: (d) => d.minimo_constitucional,
    },
    { chave: "empenhado", rotulo: "(+) ASPS Empenhado", tipo: "moeda", valor: (d) => d.despesa_asps_empenhada },
    { chave: "liquidado", rotulo: "(+) ASPS Liquidado", tipo: "moeda", valor: (d) => d.despesa_asps_liquidada },
    { chave: "pago", rotulo: "(+) ASPS Pago", tipo: "moeda", valor: (d) => d.despesa_asps_paga },
    {
      chave: "indice_stn",
      rotulo: "ÍNDICE STN",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_aplicado,
    },
    {
      chave: "indice_gerencial",
      rotulo: "ÍNDICE GERENCIAL 1 (Empenhada)",
      tipo: "percentual",
      destaque: true,
      valor: (d) => d.percentual_gerencial,
    },
  ];
}

function linhasVAATEducacaoInfantil(): LinhaPivot<ApuracaoVAATEducacaoInfantil>[] {
  return [
    { chave: "exigido", rotulo: "Valor Exigido", tipo: "moeda", valor: (d) => d.valor_exigido },
    { chave: "aplicado", rotulo: "Valor Aplicado", tipo: "moeda", negrito: true, valor: (d) => d.valor_aplicado },
    {
      chave: "indice",
      rotulo: "% Aplicado",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_aplicado,
    },
    {
      chave: "pct_vaat_publicado",
      rotulo: "% VAAT Publicado (MEC/MF)",
      tipo: "percentual",
      valor: (d) => d.percentual_vaat_publicado,
    },
    {
      chave: "portaria_vaat",
      rotulo: "Portaria de Referência",
      tipo: "texto",
      valor: (d) => d.portaria_vaat_referencia,
    },
  ];
}

function linhasVAATDespesaCapital(): LinhaPivot<ApuracaoVAATDespesaCapital>[] {
  return [
    { chave: "exigido", rotulo: "Valor Exigido (15%)", tipo: "moeda", valor: (d) => d.valor_exigido },
    { chave: "aplicado", rotulo: "Valor Aplicado", tipo: "moeda", negrito: true, valor: (d) => d.valor_aplicado },
    {
      chave: "indice",
      rotulo: "% Aplicado",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_aplicado,
    },
  ];
}

function linhasFundebNaoAplicado(): LinhaPivot<ApuracaoValorNaoAplicadoFundeb>[] {
  return [
    {
      chave: "max_permitido",
      rotulo: "Valor Máximo Permitido (10% de Superávit)",
      tipo: "moeda",
      valor: (d) => d.valor_maximo_permitido,
    },
    { chave: "nao_aplicado", rotulo: "Valor Não Aplicado", tipo: "moeda", valor: (d) => d.valor_nao_aplicado },
    {
      chave: "nao_aplicado_ajuste",
      rotulo: "Valor Não Aplicado Após Ajuste",
      tipo: "moeda",
      valor: (d) => d.valor_nao_aplicado_apos_ajuste,
    },
    {
      chave: "excedente",
      rotulo: "(=) Excedente ao Máximo Permitido",
      tipo: "moeda",
      negrito: true,
      destaque: true,
      valor: (d) => d.valor_excedente_ao_maximo_permitido,
    },
    {
      chave: "percentual",
      rotulo: "% Não Aplicado",
      tipo: "percentual",
      negrito: true,
      destaque: true,
      valor: (d) => d.percentual_nao_aplicado,
    },
  ];
}

// As 7 fontes que compõem o superávit do FUNDEB reprogramado — mesma lista
// de `FONTES_SUPERAVIT_FUNDEB` em `apps/importacao/services.py` (backend).
const FONTES_SUPERAVIT_FUNDEB = [
  "25400000", "25401070", "25410000", "25411070", "25420000", "25430000", "25460000",
];

interface FonteNoMes {
  nome: string;
  liquidado: number;
  empenhado: number;
}

// `fontesPorMes[mes][codigo]` — agregado das 7 fontes de superávit do
// FUNDEB nos meses 2 e 4, os dois únicos usados pelo "Aplicado até o 1º
// Quadrimestre" (ver `mesAlvoAplicado1Q` abaixo). Agrupamento client-side a
// partir de `/execucao-orcamentaria/` já fetchado — mesmo padrão de
// agrupar-por-fonte client-side já usado em outras páginas (ex.
// `RelatorioFinanceiroPage.tsx`).
function agruparPorFonte(lancamentos: LancamentoExecucaoOrcamentaria[]): Record<string, FonteNoMes> {
  const mapa: Record<string, FonteNoMes> = {};
  for (const l of lancamentos) {
    const r = l.rubrica_detalhe;
    if (!FONTES_SUPERAVIT_FUNDEB.includes(r.fonte_recursos_codigo)) continue;
    if (!mapa[r.fonte_recursos_codigo]) {
      mapa[r.fonte_recursos_codigo] = { nome: r.fonte_recursos_nome, liquidado: 0, empenhado: 0 };
    }
    mapa[r.fonte_recursos_codigo].liquidado += Number(l.liquidado_acumulado);
    mapa[r.fonte_recursos_codigo].empenhado += Number(l.empenhado_acumulado);
  }
  return mapa;
}

// Bimestre 1 fecha em fevereiro, antes do 1º quadrimestre fechar — o
// próprio RREO-Anexo 8 mostra, só pra esse bimestre, o liquidado parcial
// até fevereiro (confirmado batendo exatamente: R$546.585,80 = liquidado
// acumulado em fevereiro nessas 7 fontes). Do bimestre 2 em diante o valor
// trava em abril (quadrimestre já fechado). A visão gerencial (empenhado)
// não tem essa distinção — o cálculo no backend sempre usa abril (ver
// `_calcular_gerencial_empenhado_reprogramacao`).
function mesAlvoAplicado1Q(bimestre: number, mostrarEmpenhado: boolean): 2 | 4 {
  if (mostrarEmpenhado) return 4;
  return bimestre <= 1 ? 2 : 4;
}

// A quebra por origem (19.1 impostos / 19.2 União) foi removida da tabela
// pivot a pedido do usuário — o layout do RREO-Anexo 8 de 2026 parou de
// imprimir esses sub-itens (ver CLAUDE.md, "Relatório RREO-Anexo 8 de 2026
// mudou de layout"), então `ApuracaoReprogramacaoFundebOrigem` fica sempre
// vazia pra todo bimestre de 2026 — as duas linhas só mostravam "—" em
// branco. `d.origens` (e o tipo `ApuracaoReprogramacaoFundebOrigem`) não
// são mais usados aqui; a tabela filha continua existindo no backend/API
// pra quando/se o ASPEC voltar a imprimir o detalhamento.
//
// `mostrarEmpenhado` alterna as 2 linhas de "aplicado" entre a visão
// oficial (liquidado) e a visão GERENCIAL (empenhado) — mesmo toggle da
// visão sintética (`ExecucaoFiscalPage.tsx`, `construirConfigReprogramacao`).
// `fontesPorMes` detalha "(=) Aplicado até o 1º Quadrimestre" por fonte
// (pedido do usuário) — "Aplicado Após" não tem quebra por fonte ainda.
function linhasFundebReprogramacao(
  mostrarEmpenhado: boolean,
  fontesPorMes: Record<number, Record<string, FonteNoMes>>
): LinhaPivot<ApuracaoReprogramacaoFundeb>[] {
  const sufixoRotulo = mostrarEmpenhado ? " (Gerencial — Empenhado)" : "";

  const filhosPorFonte: LinhaPivot<ApuracaoReprogramacaoFundeb>[] = FONTES_SUPERAVIT_FUNDEB.map((codigo) => ({
    chave: `fonte_${codigo}`,
    rotulo: `${codigo} - ${fontesPorMes[4]?.[codigo]?.nome ?? fontesPorMes[2]?.[codigo]?.nome ?? codigo}`,
    tipo: "moeda",
    valor: (d) => {
      const mes = mesAlvoAplicado1Q(d.bimestre, mostrarEmpenhado);
      const fonte = fontesPorMes[mes]?.[codigo];
      if (!fonte) return undefined;
      return mostrarEmpenhado ? fonte.empenhado : fonte.liquidado;
    },
  }));

  return [
    {
      chave: "superavit_permitido",
      rotulo: "Superávit Permitido (Exercício Anterior)",
      tipo: "moeda",
      valor: (d) => d.valor_superavit_permitido_exercicio_anterior,
    },
    {
      chave: "nao_aplicado_ant",
      rotulo: "Não Aplicado (Exercício Anterior)",
      tipo: "moeda",
      valor: (d) => d.valor_nao_aplicado_exercicio_anterior,
    },
    {
      chave: "aplicado_1q",
      rotulo: `(=) Aplicado até o 1º Quadrimestre${sufixoRotulo}`,
      tipo: "moeda",
      negrito: true,
      valor: (d) =>
        mostrarEmpenhado
          ? d.valor_aplicado_ate_primeiro_quadrimestre_empenhado
          : d.valor_aplicado_ate_primeiro_quadrimestre,
      filhos: filhosPorFonte,
    },
    {
      chave: "aplicado_apos_1q",
      rotulo: `Aplicado Após o 1º Quadrimestre${sufixoRotulo}`,
      tipo: "moeda",
      valor: (d) =>
        mostrarEmpenhado
          ? d.valor_aplicado_apos_primeiro_quadrimestre_empenhado
          : d.valor_aplicado_apos_primeiro_quadrimestre,
    },
    // "Saldo a Aplicar (até o 1º Quadrimestre Atual)" foi tirado desta
    // tabela pivotada a pedido do usuário — ao lado de "Aplicado Após o 1º
    // Quadrimestre" (que cresce a cada bimestre), o saldo travado no valor
    // de abril (ver `cumpre_limite`/`_saldo_a_aplicar` no backend) parecia
    // quebrado/sem sentido visualmente. O campo continua existindo no
    // backend e em `ExecucaoFiscalPage.tsx` (visão sintética) — é a base
    // real de `cumpre_limite`, só não aparece mais aqui.
  ];
}

function porBimestre<T extends { bimestre: number }>(dados: T[]): Record<number, T> {
  return Object.fromEntries(dados.map((d) => [d.bimestre, d]));
}

// Regressão linear simples (mínimos quadrados) sobre os pontos (bimestre,
// valor) já conhecidos, extrapolada pro `xAlvo` — usada pra projetar o 6º
// bimestre do MDE com base na evolução real dos 5 anteriores, em vez de só
// repetir o último valor ou aplicar uma regra de três ingênua (valor do
// bim.5 × 12/10), que ignoraria se a série está acelerando/desacelerando.
// Taxa mensal média implícita nos bimestres já importados — pra cada
// bimestre i, o valor já é ACUMULADO desde o início do exercício, e i×2
// é o mês de fechamento daquele bimestre (mesma convenção usada em todo
// o resto do app, ex. `mesFechamento = bimestre * 2` em
// `apps/importacao/services.py`). `valor_acumulado_i / (i×2)` dá a taxa
// mensal média implícita até ali; a média dessas taxas nos 5 bimestres
// suaviza meses atípicos (ex. um bimestre com um pico isolado) em vez de
// deixar um único ponto fora da curva distorcer a projeção inteira.
function taxaMensalMedia(pontos: { bimestre: number; valor: number }[]): number {
  const taxas = pontos.map((p) => p.valor / (p.bimestre * 2));
  return taxas.reduce((soma, t) => soma + t, 0) / taxas.length;
}

// Projeta um registro sintético de bimestre 6 a partir dos bimestres já
// importados — genérico por design (não lista campo por campo): parte de
// uma cópia do último bimestre real (preserva metadados/arrays/texto como
// `itens_receita`, `municipio_nome` etc.) e, pra cada chave cujo valor é
// uma string numérica em pelo menos 1 bimestre, soma ao valor ACUMULADO
// do último bimestre real (normalmente o 5º, mês 10) a taxa mensal média
// (ver acima, calculada sobre todos os meses já conhecidos) vezes os
// meses que ainda faltam até o fechamento do bimestre 6 (normalmente
// novembro+dezembro = 2 meses) — ou seja, confia no valor acumulado real
// como base e só estima o INCREMENTO dos meses que faltam, em vez de
// extrapolar o ano inteiro a partir só da taxa média (que distorcia mais
// em séries não-lineares). Campos sem nenhum ponto numérico (texto,
// array, boolean) ficam com o valor do último bimestre real, sem
// projeção. Nunca roda se já existe um bimestre 6 de verdade (ver
// `mdeComProjecao` abaixo).
function projetarBimestre6<T extends { bimestre: number }>(dados: T[]): T | null {
  if (dados.length === 0) return null;
  const ordenados = dados.slice().sort((a, b) => a.bimestre - b.bimestre);
  const ultimo = ordenados[ordenados.length - 1];
  const mesesRestantes = (6 - ultimo.bimestre) * 2;
  const projetado: Record<string, unknown> = { ...ultimo, bimestre: 6 };
  for (const chave of Object.keys(ultimo as Record<string, unknown>)) {
    if (chave === "bimestre") continue;
    const pontos = ordenados
      .map((d) => ({ bimestre: d.bimestre, valor: (d as unknown as Record<string, unknown>)[chave] }))
      .filter(
        (p): p is { bimestre: number; valor: string } =>
          typeof p.valor === "string" && p.valor !== "" && !Number.isNaN(Number(p.valor))
      )
      .map((p) => ({ bimestre: p.bimestre, valor: Number(p.valor) }));
    if (pontos.length >= 1) {
      const valorUltimo = pontos[pontos.length - 1].valor;
      projetado[chave] = String(valorUltimo + taxaMensalMedia(pontos) * mesesRestantes);
    }
  }

  // `base_calculo` e `minimo_constitucional` também são CALCULADOS, não
  // projetados independentemente — confirmado via shell contra os 5
  // bimestres reais: `base_calculo` é SEMPRE `receita_impostos +
  // receita_transferencias` (bate exato nos 5) e `minimo_constitucional`
  // é SEMPRE `base_calculo × 25%` (bate em 3 dos 5 à centavo, 2 com
  // diferença de R$0,01 — arredondamento do próprio relatório, não erro
  // de fórmula). Precisa rodar ANTES dos overrides de `valor_exigido`
  // (que usa `minimo_constitucional`) e do recálculo de percentuais (que
  // usa `base_calculo` como denominador) logo abaixo.
  if ("base_calculo" in projetado && "receita_impostos" in projetado && "receita_transferencias" in projetado) {
    projetado.base_calculo = String(
      Number(projetado.receita_impostos as string) + Number(projetado.receita_transferencias as string)
    );
  }
  if ("minimo_constitucional" in projetado && "base_calculo" in projetado) {
    projetado.minimo_constitucional = String(Number(projetado.base_calculo as string) * 0.25);
  }

  // `valor_exigido` também não é projetado independentemente — é
  // CALCULADO a partir de `minimo_constitucional`, confirmado via shell
  // contra os 5 bimestres reais: são sempre idênticos, à centavo.
  if ("valor_exigido" in projetado && "minimo_constitucional" in projetado) {
    projetado.valor_exigido = projetado.minimo_constitucional;
  }

  // TOTAL STN (`valor_aplicado`) e ÍNDICE STN (`percentual_aplicado`) são
  // os ÚNICOS campos do MDE que vêm do RREO literal, sem equivalente
  // calculável com confiança pro 6º bimestre (não existe relatório real
  // pra ele ainda) — pedido do usuário: ficam ZERADOS na projeção em vez
  // de mostrar um valor estimado sob um rótulo que sugere "oficial". As
  // variantes GERENCIAL (baseadas em despesa empenhada/liquidada/paga +
  // FUNDEB) continuam projetadas normalmente — são sempre estimativas por
  // natureza, então não têm esse problema de rótulo.
  if ("valor_aplicado" in projetado) projetado.valor_aplicado = "0";
  if ("percentual_aplicado" in projetado) projetado.percentual_aplicado = "0";

  // Os índices GERENCIAIS em % NÃO são projetados pela taxa mensal como
  // os campos monetários acima — um percentual não "acumula" mês a mês,
  // então extrapolá-lo direto dava um número desligado da própria base
  // de cálculo projetada. Em vez disso, são CALCULADOS a partir dos
  // campos monetários já projetados acima, com a mesma fórmula que o
  // backend já usa pros bimestres reais (`indice_gerencial_N =
  // total_gerencial_N / base_calculo * 100`, ver
  // `apps/execucao_fiscal/models.py`) — garante que índice e total
  // projetados sempre batem entre si.
  const baseCalculoProjetada = Number(projetado.base_calculo as string);
  function percentualCalculado(chaveNumerador: string): string {
    if (!baseCalculoProjetada) return "0";
    const numerador = Number(projetado[chaveNumerador] as string);
    return String((numerador / baseCalculoProjetada) * 100);
  }
  if ("indice_gerencial_1" in projetado) projetado.indice_gerencial_1 = percentualCalculado("total_gerencial_1");
  if ("indice_gerencial_2" in projetado) projetado.indice_gerencial_2 = percentualCalculado("total_gerencial_2");
  if ("indice_gerencial_3" in projetado) projetado.indice_gerencial_3 = percentualCalculado("total_gerencial_3");
  if ("indice_gerencial_1_desconsiderando_pnae" in projetado) {
    projetado.indice_gerencial_1_desconsiderando_pnae = percentualCalculado("total_gerencial_1_desconsiderando_pnae");
  }
  if ("indice_gerencial_2_desconsiderando_pnae" in projetado) {
    projetado.indice_gerencial_2_desconsiderando_pnae = percentualCalculado("total_gerencial_2_desconsiderando_pnae");
  }
  if ("indice_gerencial_3_desconsiderando_pnae" in projetado) {
    projetado.indice_gerencial_3_desconsiderando_pnae = percentualCalculado("total_gerencial_3_desconsiderando_pnae");
  }
  return projetado as unknown as T;
}

const INDICES = [
  { chave: "dtp", rotulo: "DTP" },
  { chave: "mde", rotulo: "MDE" },
  { chave: "magisterio", rotulo: "Magistério/FUNDEB" },
  { chave: "eti", rotulo: "FUNDEB ETI (4%)" },
  { chave: "asps", rotulo: "ASPS" },
  { chave: "vaat_ed_infantil", rotulo: "VAAT Educação Infantil" },
  { chave: "vaat_capital", rotulo: "VAAT Despesa de Capital" },
  { chave: "fundeb_nao_aplicado", rotulo: "FUNDEB Não Aplicado" },
  { chave: "fundeb_reprogramacao", rotulo: "FUNDEB Reprogramação" },
] as const;

type IndiceChave = (typeof INDICES)[number]["chave"];

// Tipo local, só usado nesta página (gerenciamento da flag PNAE/PEAE direto
// no demonstrativo do MDE) — não precisa entrar em `api/types.ts`.
interface AcaoPNAE {
  id: number;
  codigo: string;
  nome: string;
  funcao_codigo: string | null;
  desconsiderar_pnae_peae: boolean;
}

export function ExecucaoFiscalDetalhadoPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [indice, setIndice] = useState<IndiceChave>("dtp");
  const [reprogramacaoEmpenhado, setReprogramacaoEmpenhado] = useState(false);
  const [modoExibicao, setModoExibicao] = useState<ModoExibicao>("valores");
  const [dialogoPnaeAberto, setDialogoPnaeAberto] = useState(false);
  // Desligado = bate com o RREO oficial, sem descontar nada; ligado =
  // visão gerencial mais restritiva, descontando PNAE/PEAE + Ensino
  // Médio/Superior (362/364) em recursos próprios — mesmo padrão de
  // "Considerar despesa empenhada" já usado na Reprogramação/VAAT.
  // Padrão LIGADO por pedido explícito do usuário (a visão gerencial é a
  // que deve valer por padrão, inclusive no Resumo Geral).
  const [desconsiderarPnaeEnsinoMedioSuperior, setDesconsiderarPnaeEnsinoMedioSuperior] = useState(true);
  // Padrão DESLIGADO (pedido explícito do usuário) — ao contrário do
  // switch acima, essa é uma estimativa, não deve aparecer sem o usuário
  // pedir.
  const [projetarSextoBimestre, setProjetarSextoBimestre] = useState(false);
  const [dialogoBim6Aberto, setDialogoBim6Aberto] = useState(false);
  const [valoresBim6, setValoresBim6] = useState<Record<string, string>>({});
  const [salvandoBim6, setSalvandoBim6] = useState(false);
  const [erroBim6, setErroBim6] = useState<string | null>(null);
  // Campo do diálogo do 6º bimestre que está com foco no momento — enquanto
  // focado mostra o valor "cru" (editável); ao desfocar, reformata com
  // separador de milhar (pt-BR). Evita o problema clássico de reformatar a
  // cada tecla digitada (cursor pula de lugar).
  const [campoFocadoBim6, setCampoFocadoBim6] = useState<string | null>(null);
  const [acoesPnae, setAcoesPnae] = useState<AcaoPNAE[]>([]);
  const [carregandoAcoesPnae, setCarregandoAcoesPnae] = useState(false);
  const [recalculandoPnae, setRecalculandoPnae] = useState(false);

  const [dtp, setDtp] = useState<ApuracaoDTP[]>([]);
  const [mde, setMde] = useState<ApuracaoMDE[]>([]);
  const [magisterio, setMagisterio] = useState<ApuracaoMagisterioFundeb[]>([]);
  const [eti, setEti] = useState<ApuracaoETIFundeb[]>([]);
  const [asps, setAsps] = useState<ApuracaoASPS[]>([]);
  const [vaatEdInfantil, setVaatEdInfantil] = useState<ApuracaoVAATEducacaoInfantil[]>([]);
  const [vaatCapital, setVaatCapital] = useState<ApuracaoVAATDespesaCapital[]>([]);
  const [fundebNaoAplicado, setFundebNaoAplicado] = useState<ApuracaoValorNaoAplicadoFundeb[]>([]);
  const [fundebReprogramacao, setFundebReprogramacao] = useState<ApuracaoReprogramacaoFundeb[]>([]);
  const [fontesReprogramacaoPorMes, setFontesReprogramacaoPorMes] = useState<Record<number, Record<string, FonteNoMes>>>({});

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        setExercicios(data.results);
        const anoParam = searchParams.get("exercicio");
        const correspondente = anoParam ? data.results.find((e) => String(e.ano) === anoParam) : null;
        setExercicioId((correspondente ?? data.results[0])?.id ?? "");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [municipioSelecionadoId]);

  const exercicioSelecionado = useMemo(
    () => exercicios.find((e) => e.id === exercicioId) ?? null,
    [exercicios, exercicioId]
  );

  useEffect(() => {
    if (!municipioSelecionadoId || !exercicioSelecionado) return;
    const params = { municipio: municipioSelecionadoId, exercicio: exercicioSelecionado.ano };
    buscarTodasPaginas<ApuracaoDTP>("/apuracao-dtp/", params).then(setDtp);
    buscarTodasPaginas<ApuracaoMDE>("/apuracao-mde/", params).then(setMde);
    buscarTodasPaginas<ApuracaoMagisterioFundeb>("/apuracao-magisterio-fundeb/", params).then(setMagisterio);
    buscarTodasPaginas<ApuracaoASPS>("/apuracao-asps/", params).then(setAsps);
    buscarTodasPaginas<ApuracaoETIFundeb>("/apuracao-fundeb-eti/", params).then(setEti);
    buscarTodasPaginas<ApuracaoVAATEducacaoInfantil>("/apuracao-vaat-educacao-infantil/", params).then(setVaatEdInfantil);
    buscarTodasPaginas<ApuracaoVAATDespesaCapital>("/apuracao-vaat-despesa-capital/", params).then(setVaatCapital);
    buscarTodasPaginas<ApuracaoValorNaoAplicadoFundeb>("/apuracao-fundeb-nao-aplicado/", params).then(setFundebNaoAplicado);
    buscarTodasPaginas<ApuracaoReprogramacaoFundeb>("/apuracao-fundeb-reprogramacao/", params).then(setFundebReprogramacao);
  }, [municipioSelecionadoId, exercicioSelecionado]);

  // Detalhamento por fonte de "(=) Aplicado até o 1º Quadrimestre" — só
  // precisa dos meses 2 (fecha o bimestre 1, antes do quadrimestre fechar)
  // e 4 (fechamento do 1º quadrimestre, valor trava aqui do bim.2 em
  // diante) — ver `mesAlvoAplicado1Q`. Independente do `loa_id` existir,
  // já que `/execucao-orcamentaria/` exige esse filtro pra não trazer
  // todo o histórico acessível ao usuário.
  useEffect(() => {
    if (!exercicioSelecionado?.loa_id) {
      setFontesReprogramacaoPorMes({});
      return;
    }
    const loaId = exercicioSelecionado.loa_id;
    Promise.all([
      buscarTodasPaginas<LancamentoExecucaoOrcamentaria>("/execucao-orcamentaria/", { loa: loaId, mes_referencia: 2 }),
      buscarTodasPaginas<LancamentoExecucaoOrcamentaria>("/execucao-orcamentaria/", { loa: loaId, mes_referencia: 4 }),
    ]).then(([mes2, mes4]) => {
      setFontesReprogramacaoPorMes({ 2: agruparPorFonte(mes2), 4: agruparPorFonte(mes4) });
    });
  }, [exercicioSelecionado]);

  // Gerenciamento da flag `Acao.desconsiderar_pnae_peae` direto no
  // demonstrativo do MDE (pedido do usuário) — busca todas as Ações do
  // exercício e filtra client-side pra função 12 (Educação), já que
  // `Acao` não tem FK pra `Funcao` (só o backend sabe derivar
  // `funcao_codigo` via a primeira `RubricaOrcamentaria`, ver CLAUDE.md).
  function abrirDialogoPnae() {
    setDialogoPnaeAberto(true);
    if (!exercicioSelecionado?.loa_id) return;
    setCarregandoAcoesPnae(true);
    buscarTodasPaginas<AcaoPNAE>("/acoes/", { loa: exercicioSelecionado.loa_id, page_size: 200 })
      .then((todas) => {
        setAcoesPnae(
          todas.filter((a) => a.funcao_codigo === "12").sort((a, b) => a.codigo.localeCompare(b.codigo))
        );
      })
      .finally(() => setCarregandoAcoesPnae(false));
  }

  function alternarPnae(acaoId: number, novoValor: boolean) {
    setAcoesPnae((lista) => lista.map((a) => (a.id === acaoId ? { ...a, desconsiderar_pnae_peae: novoValor } : a)));
    api.patch(`/acoes/${acaoId}/`, { desconsiderar_pnae_peae: novoValor });
  }

  async function recalcularPnaeEFechar() {
    if (!municipioSelecionadoId || !exercicioSelecionado) return;
    setRecalculandoPnae(true);
    try {
      await api.post(
        "/apuracao-mde/recalcular-mde-derivados/",
        {},
        { params: { municipio: municipioSelecionadoId, exercicio: exercicioSelecionado.ano } }
      );
      const params = { municipio: municipioSelecionadoId, exercicio: exercicioSelecionado.ano };
      await buscarTodasPaginas<ApuracaoMDE>("/apuracao-mde/", params).then(setMde);
      setDialogoPnaeAberto(false);
    } finally {
      setRecalculandoPnae(false);
    }
  }

  // Projeção do 6º bimestre do MDE — só adiciona o registro sintético se
  // o switch estiver ligado, houver pelo menos 2 bimestres reais pra
  // calcular a regressão, e ainda NÃO existir um bimestre 6 de verdade
  // (se um dia for importado, o dado real sempre vence, nunca a projeção).
  const mdeComProjecao = useMemo(() => {
    if (!projetarSextoBimestre || mde.some((d) => d.bimestre === 6)) return mde;
    const projecao = projetarBimestre6(mde);
    return projecao ? [...mde, projecao] : mde;
  }, [mde, projetarSextoBimestre]);

  // Se já existe um bimestre 6 de verdade (origem MANUAL, criado por essa
  // mesma tela ou futuramente por um RREO real), o diálogo abaixo edita
  // (PATCH) esse registro em vez de criar outro — `ApuracaoMDE` já tem uma
  // constraint de unicidade (município, exercício, bimestre), então criar
  // de novo falharia mesmo se tentasse.
  const mdeBim6Real = mde.find((d) => d.bimestre === 6) ?? null;

  function abrirDialogoBim6() {
    const base = mdeBim6Real ?? projetarBimestre6(mde);
    const iniciais: Record<string, string> = {};
    for (const campo of CAMPOS_MDE) {
      const valor = base ? (base as unknown as Record<string, unknown>)[campo.chave] : undefined;
      iniciais[campo.chave] = typeof valor === "string" ? String(Number(valor).toFixed(2)) : "0";
    }
    setValoresBim6(iniciais);
    setErroBim6(null);
    setDialogoBim6Aberto(true);
  }

  async function salvarBim6() {
    if (!municipioSelecionadoId || !exercicioSelecionado) return;
    setSalvandoBim6(true);
    setErroBim6(null);
    try {
      const payload: Record<string, string | number> = {
        municipio: municipioSelecionadoId,
        exercicio: exercicioSelecionado.ano,
        bimestre: 6,
      };
      for (const campo of CAMPOS_MDE) {
        payload[campo.chave] = valoresBim6[campo.chave] || "0";
      }
      if (mdeBim6Real) {
        await api.patch(`/apuracao-mde/${mdeBim6Real.id}/`, payload);
      } else {
        await api.post("/apuracao-mde/", payload);
      }
      const params = { municipio: municipioSelecionadoId, exercicio: exercicioSelecionado.ano };
      await buscarTodasPaginas<ApuracaoMDE>("/apuracao-mde/", params).then(setMde);
      setDialogoBim6Aberto(false);
    } catch {
      setErroBim6("Não foi possível salvar. Confira os valores informados.");
    } finally {
      setSalvandoBim6(false);
    }
  }

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
        <IconButton onClick={() => navigate("/execucao-fiscal")} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h5">Execução Fiscal — Detalhado</Typography>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap", alignItems: "center" }}>
        <Select
          size="small"
          value={exercicioId}
          onChange={(e) => setExercicioId(Number(e.target.value))}
          displayEmpty
          sx={{ minWidth: 160 }}
        >
          {exercicios.length === 0 && <MenuItem value="">Sem exercícios</MenuItem>}
          {exercicios.map((ex) => (
            <MenuItem key={ex.id} value={ex.id}>
              Exercício {ex.ano}
            </MenuItem>
          ))}
        </Select>
        <Button variant="text" size="small" onClick={() => navigate("/execucao-fiscal")}>
          Ver Versão Sintética
        </Button>
      </Box>

      <Tabs value={indice} onChange={(_, v) => setIndice(v)} sx={{ mb: 2 }}>
        {INDICES.map((i) => (
          <Tab key={i.chave} value={i.chave} label={i.rotulo} />
        ))}
      </Tabs>

      <ToggleButtonGroup
        size="small"
        exclusive
        value={modoExibicao}
        onChange={(_, novo: ModoExibicao | null) => {
          if (novo) setModoExibicao(novo);
        }}
        sx={{ mb: 2 }}
      >
        <ToggleButton value="valores">Valores</ToggleButton>
        <ToggleButton value="valores_variacao">Valores + Variação</ToggleButton>
        <ToggleButton value="crescimento">Crescimento entre Bimestres</ToggleButton>
      </ToggleButtonGroup>

      {indice === "dtp" && (
        <TabelaPivot linhas={linhasDTP()} dadosPorBimestre={porBimestre(dtp)} modo={modoExibicao} />
      )}
      {indice === "mde" && (
        <>
          <Box sx={{ mb: 1, display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
            <Button size="small" variant="outlined" startIcon={<RestaurantIcon />} onClick={abrirDialogoPnae}>
              Gerenciar Ações PNAE/PEAE
            </Button>
            <FormControlLabel
              control={
                <Switch
                  checked={desconsiderarPnaeEnsinoMedioSuperior}
                  onChange={(e) => setDesconsiderarPnaeEnsinoMedioSuperior(e.target.checked)}
                />
              }
              label="Desconsiderar PNAE/PEAE e Ensino Médio/Superior (362/364) no MDE"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={projetarSextoBimestre}
                  onChange={(e) => setProjetarSextoBimestre(e.target.checked)}
                />
              }
              label="Projetar 6º Bimestre (5º bimestre + taxa mensal média × 2 meses)"
            />
            <Button size="small" variant="outlined" startIcon={<EditIcon />} onClick={abrirDialogoBim6}>
              {mdeBim6Real ? "Editar 6º Bimestre" : "Criar 6º Bimestre (real)"}
            </Button>
          </Box>
          <TabelaPivot
            linhas={linhasMDE(desconsiderarPnaeEnsinoMedioSuperior)}
            dadosPorBimestre={porBimestre(mdeComProjecao)}
            modo={modoExibicao}
            colunaProjetada={
              projetarSextoBimestre && !mdeBim6Real && mdeComProjecao.some((d) => d.bimestre === 6) ? 6 : undefined
            }
          />
        </>
      )}
      {indice === "magisterio" && (
        <TabelaPivot
          linhas={linhasMagisterio()} dadosPorBimestre={porBimestre(magisterio)} modo={modoExibicao}
        />
      )}
      {indice === "eti" && (
        <TabelaPivot linhas={linhasETIFundeb()} dadosPorBimestre={porBimestre(eti)} modo={modoExibicao} />
      )}
      {indice === "asps" && (
        <TabelaPivot linhas={linhasASPS()} dadosPorBimestre={porBimestre(asps)} modo={modoExibicao} />
      )}
      {indice === "vaat_ed_infantil" && (
        <TabelaPivot
          linhas={linhasVAATEducacaoInfantil()} dadosPorBimestre={porBimestre(vaatEdInfantil)}
          modo={modoExibicao}
        />
      )}
      {indice === "vaat_capital" && (
        <TabelaPivot
          linhas={linhasVAATDespesaCapital()} dadosPorBimestre={porBimestre(vaatCapital)}
          modo={modoExibicao}
        />
      )}
      {indice === "fundeb_nao_aplicado" && (
        <TabelaPivot
          linhas={linhasFundebNaoAplicado()} dadosPorBimestre={porBimestre(fundebNaoAplicado)}
          modo={modoExibicao}
        />
      )}
      {indice === "fundeb_reprogramacao" && (
        <>
          <FormControlLabel
            sx={{ mb: 1 }}
            control={
              <Switch
                checked={reprogramacaoEmpenhado}
                onChange={(e) => setReprogramacaoEmpenhado(e.target.checked)}
              />
            }
            label="Considerar despesa empenhada (gerencial)"
          />
          <TabelaPivot
            linhas={linhasFundebReprogramacao(reprogramacaoEmpenhado, fontesReprogramacaoPorMes)}
            dadosPorBimestre={porBimestre(fundebReprogramacao)}
            modo={modoExibicao}
          />
        </>
      )}

      <Dialog open={dialogoPnaeAberto} onClose={() => setDialogoPnaeAberto(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Ações de Educação (função 12) — Desconsiderar PNAE e PEAE</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Marque as ações cujo gasto com PNAE/PEAE em recursos próprios (fontes 15001001/25001001) não deve contar
            como aplicação em MDE. Alterações são salvas na hora; clique em "Recalcular e Fechar" para refletir no
            demonstrativo.
          </Typography>
          {carregandoAcoesPnae && <Typography variant="body2">Carregando...</Typography>}
          {!carregandoAcoesPnae && acoesPnae.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              Nenhuma ação encontrada na função 12 para este exercício.
            </Typography>
          )}
          {acoesPnae.map((a) => (
            <FormControlLabel
              key={a.id}
              sx={{ display: "flex", width: "100%" }}
              control={
                <Checkbox
                  checked={a.desconsiderar_pnae_peae}
                  onChange={(e) => alternarPnae(a.id, e.target.checked)}
                />
              }
              label={`${a.codigo} - ${a.nome}`}
            />
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogoPnaeAberto(false)}>Fechar sem recalcular</Button>
          <Button variant="contained" disabled={recalculandoPnae} onClick={recalcularPnaeEFechar}>
            {recalculandoPnae ? "Recalculando..." : "Recalcular e Fechar"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={dialogoBim6Aberto} onClose={() => setDialogoBim6Aberto(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{mdeBim6Real ? "Editar 6º Bimestre" : "Criar 6º Bimestre"} — MDE</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {erroBim6 && <Alert severity="error">{erroBim6}</Alert>}
          <Typography variant="body2" color="text.secondary">
            {mdeBim6Real
              ? "Ajuste os valores reais do 6º bimestre."
              : "Os campos já vêm preenchidos com a projeção (5º bimestre + taxa mensal média × 2 meses, ref. novembro/dezembro) — ajuste o que for preciso antes de salvar. Ao salvar, o 6º bimestre vira um registro real (origem manual), deixa de ser projeção e passa a valer em toda a aplicação (Resumo Geral, PDF etc.)."}
          </Typography>
          {CAMPOS_MDE.map((campo) => {
            // Único campo percentual entre os 15 — os demais são todos
            // monetários (ver CAMPOS_MDE). Mostra o prefixo/sufixo certo
            // em vez de deixar o número solto sem unidade.
            const ehPercentual = campo.chave === "percentual_aplicado";
            const valorCru = valoresBim6[campo.chave] ?? "";
            const focado = campoFocadoBim6 === campo.chave;
            return (
              <TextField
                key={campo.chave}
                label={campo.rotulo}
                type="text"
                inputMode="decimal"
                value={focado ? valorCru : formatarValorEntrada(valorCru || "0")}
                onFocus={() => setCampoFocadoBim6(campo.chave)}
                onBlur={() => setCampoFocadoBim6(null)}
                onChange={(e) =>
                  setValoresBim6((v) => ({ ...v, [campo.chave]: normalizarValorEntrada(e.target.value) }))
                }
                fullWidth
                slotProps={{
                  input: ehPercentual
                    ? { endAdornment: <InputAdornment position="end">%</InputAdornment> }
                    : { startAdornment: <InputAdornment position="start">R$</InputAdornment> },
                }}
              />
            );
          })}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogoBim6Aberto(false)}>Cancelar</Button>
          <Button variant="contained" disabled={salvandoBim6} onClick={salvarBim6}>
            {salvandoBim6 ? "Salvando..." : "Salvar"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
