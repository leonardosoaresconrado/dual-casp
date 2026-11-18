import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Select,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import TableChartIcon from "@mui/icons-material/TableChart";
import SummarizeIcon from "@mui/icons-material/Summarize";
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
  CampoOrigemRegistro,
  Exercicio,
} from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { useParametro } from "../parametros/ParametrosContext";
import { AcoesRegistroManual, type CampoEdicao } from "../components/AcoesRegistroManual";
import { CAMPOS_MDE } from "./camposApuracaoMDE";
import { AZUL_SEQUENCIAL, ChartTooltip, GRID_LINE, INK_MUTED } from "../components/charts/GraficoLinhaTendencia";

function formatarMoeda(valor: string | number): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarPercentual(valor: string | number): string {
  return `${Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function formatarPercentualGrafico(valor: number): string {
  return `${valor.toFixed(1)}%`;
}

interface PontoBarraLimite {
  bimestre: number;
  valor: number;
  cumpreLimite: boolean;
}

function paraBarraLimite<T extends { bimestre: number; cumpre_limite: boolean }>(
  dados: T[],
  valor: (d: T) => number
): PontoBarraLimite[] {
  return dados
    .slice()
    .sort((a, b) => a.bimestre - b.bimestre)
    .map((d) => ({ bimestre: d.bimestre, valor: valor(d), cumpreLimite: d.cumpre_limite }));
}

// `minimoOuMaximoLabel` é texto livre ("mín. 25%", "máx. 54%", "sem
// excedente ao máx. de 10%") — extrai o número pra desenhar a linha de
// limite no gráfico. "conforme valor exigido" (VAAT Educação Infantil) não
// tem número fixo, então não ganha linha (null).
function extrairLimiteNumerico(rotulo: string): number | null {
  const m = rotulo.match(/(\d+(?:[.,]\d+)?)\s*%/);
  return m ? Number(m[1].replace(",", ".")) : null;
}

interface LinhaLimite {
  // `valor` — linha reta constante (a maioria dos índices, limiar fixo em
  // lei). `valoresPorBimestre` — linha conectando um valor DIFERENTE por
  // bimestre (ex.: VAAT Educação Infantil, cujo percentual oficial muda a
  // cada nova Portaria MEC/MF publicada durante o exercício — "precisamos
  // criar um parâmetro... porque ele varia no ano", pedido do usuário).
  // Exatamente um dos dois é informado.
  valor?: number;
  valoresPorBimestre?: Record<number, number>;
  rotulo: string;
  cor: string;
}

// Uma única linha de referência, cor padrão — usada por todo índice exceto
// DTP (que tem 3 limiares reais: máximo/prudencial/alerta, ver abaixo).
function linhaUnica(rotulo: string): LinhaLimite[] {
  const valor = extrairLimiteNumerico(rotulo);
  return valor === null ? [] : [{ valor, rotulo, cor: AZUL_SEQUENCIAL }];
}

// Linha de referência que MUDA de valor por bimestre — caso do VAAT
// Educação Infantil, cujo percentual oficial (base MEC/MF) é republicado
// algumas vezes por exercício, cada publicação valendo até a próxima
// (pedido do usuário: "precisamos criar um parâmetro... porque ele varia
// no ano"). Só entra um ponto por bimestre que já tenha o campo manual
// preenchido (`percentual_vaat_publicado`) — bimestres sem o dado ainda
// simplesmente não aparecem na linha, em vez de inventar um valor.
function linhaVariavelPorBimestre<T extends { bimestre: number }>(
  dados: T[],
  valor: (d: T) => string | null,
  rotulo: string,
  cor: string
): LinhaLimite[] {
  const valoresPorBimestre: Record<number, number> = {};
  for (const d of dados) {
    const v = valor(d);
    if (v !== null) valoresPorBimestre[d.bimestre] = Number(v);
  }
  return Object.keys(valoresPorBimestre).length === 0 ? [] : [{ valoresPorBimestre, rotulo, cor }];
}

// Barras = valor do índice por bimestre (verde/vermelho conforme
// cumpre_limite, mesma semântica do Chip no CardStatus, com o valor
// rotulado no topo de cada barra); linhas pontilhadas horizontais = os
// limiares constitucionais (uma ou mais), legenda por cor logo abaixo do
// título — leitura visual imediata de conformidade sem precisar olhar a
// tabela.
function GraficoBarraLimite({
  titulo,
  dados,
  linhas,
}: {
  titulo: string;
  dados: PontoBarraLimite[];
  linhas: LinhaLimite[];
}) {
  const theme = useTheme();
  const [hover, setHover] = useState<{ x: number; y: number; idx: number } | null>(null);
  const largura = 900;
  const altura = 220;
  const margem = { top: 16, right: 16, bottom: 28, left: 60 };
  const plotW = largura - margem.left - margem.right;
  const plotH = altura - margem.top - margem.bottom;

  if (dados.length === 0) {
    return (
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{titulo}</Typography>
        <Typography variant="body2" color="text.secondary">Sem dados para o período.</Typography>
      </Paper>
    );
  }

  // minValor <= 0 sempre (alguns índices podem ter % negativo num bimestre
  // isolado, ex. MDE com excedente de FUNDEB não aplicado descontando mais
  // que o empenhado) — mesma lógica de GraficoLinhaTendencia, senão uma
  // barra negativa ficava com altura 0 e o rótulo saindo fora do gráfico.
  const valoresLinhas = linhas.flatMap((l) =>
    l.valor !== undefined ? [l.valor] : Object.values(l.valoresPorBimestre ?? {})
  );
  const minValor = Math.min(0, ...dados.map((d) => d.valor));
  const maxValor = Math.max(1, ...valoresLinhas, ...dados.map((d) => d.valor)) * 1.2;
  const amplitude = maxValor - minValor || 1;
  const escalaY = (v: number) => margem.top + plotH - ((v - minValor) / amplitude) * plotH;
  const yZero = escalaY(0);
  const bandW = plotW / dados.length;
  const barW = Math.min(56, bandW * 0.5);

  const passos = 4;
  const gridY = Array.from({ length: passos + 1 }, (_, i) => margem.top + (plotH / passos) * i);

  return (
    <Paper variant="outlined" sx={{ p: 2, position: "relative" }}>
      <Typography variant="subtitle2" gutterBottom>{titulo}</Typography>
      {linhas.length > 0 && (
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 1 }}>
          {linhas.map((l) => (
            <Box key={l.rotulo} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Box sx={{ width: 14, height: 0, borderTop: `2px dashed ${l.cor}` }} />
              <Typography variant="caption" color="text.secondary">{l.rotulo}</Typography>
            </Box>
          ))}
        </Box>
      )}
      <Box sx={{ position: "relative" }}>
        <svg viewBox={`0 0 ${largura} ${altura}`} style={{ width: "100%", height: "auto", display: "block" }}>
          {gridY.map((y, i) => (
            <g key={i}>
              <line x1={margem.left} y1={y} x2={largura - margem.right} y2={y} stroke={GRID_LINE} strokeWidth={1} />
              <text x={margem.left - 8} y={y} textAnchor="end" dominantBaseline="middle" fontSize={10} fill={INK_MUTED}>
                {formatarPercentualGrafico(maxValor - (amplitude / passos) * i)}
              </text>
            </g>
          ))}
          {minValor < 0 && (
            <line x1={margem.left} y1={yZero} x2={largura - margem.right} y2={yZero} stroke={INK_MUTED} strokeWidth={1} />
          )}
          {/* Linhas de limite desenhadas ANTES das barras/rótulos de propósito —
              senão a linha pontilhada pinta por cima do texto do rótulo e o
              deixa ilegível onde os dois se cruzam (bug real, valor perto do
              limite). Com as barras (preenchimento opaco) e o texto vindo
              depois, ambos ficam sempre por cima da linha. */}
          {linhas.map((l) => {
            if (l.valor !== undefined) {
              return (
                <line
                  key={l.rotulo}
                  x1={margem.left} y1={escalaY(l.valor)} x2={largura - margem.right} y2={escalaY(l.valor)}
                  stroke={l.cor} strokeWidth={1.5} strokeDasharray="6 4"
                />
              );
            }
            // Linha variável (ex.: VAAT Educação Infantil, percentual oficial
            // muda por Portaria publicada durante o ano) — conecta um ponto
            // por bimestre em vez de uma reta constante, nos mesmos X dos
            // centros das barras.
            const pontos = dados
              .map((d, i) => {
                const v = l.valoresPorBimestre?.[d.bimestre];
                if (v === undefined) return null;
                return { x: margem.left + bandW * i + bandW / 2, y: escalaY(v) };
              })
              .filter((p): p is { x: number; y: number } => p !== null);
            if (pontos.length === 0) return null;
            const caminho = pontos.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
            return (
              <g key={l.rotulo}>
                <path d={caminho} fill="none" stroke={l.cor} strokeWidth={1.5} strokeDasharray="6 4" />
                {pontos.map((p, i) => (
                  <circle key={i} cx={p.x} cy={p.y} r={3} fill={l.cor} />
                ))}
              </g>
            );
          })}
          {dados.map((d, i) => {
            const xCentro = margem.left + bandW * i + bandW / 2;
            const x = xCentro - barW / 2;
            const yValor = escalaY(d.valor);
            const yTopo = Math.min(yValor, yZero);
            const alturaBarra = Math.abs(yValor - yZero);
            const negativo = d.valor < 0;
            const cor = d.cumpreLimite ? theme.palette.success.main : theme.palette.error.main;
            return (
              <g key={d.bimestre}>
                <text
                  x={xCentro} y={negativo ? yValor + 16 : yValor - 6}
                  textAnchor="middle" fontSize={11} fontWeight={600} fill={cor}
                >
                  {formatarPercentualGrafico(d.valor)}
                </text>
                <rect
                  x={x} y={yTopo} width={barW} height={Math.max(alturaBarra, 0)} rx={3}
                  fill={cor} opacity={hover?.idx === i ? 1 : 0.85}
                  onMouseEnter={(e) => setHover({ x: e.clientX, y: e.clientY, idx: i })}
                  onMouseMove={(e) => setHover({ x: e.clientX, y: e.clientY, idx: i })}
                  onMouseLeave={() => setHover(null)}
                  style={{ cursor: "pointer" }}
                />
                <text x={xCentro} y={margem.top + plotH + 16} textAnchor="middle" fontSize={10} fill={INK_MUTED}>
                  {d.bimestre}º bim.
                </text>
              </g>
            );
          })}
        </svg>
      </Box>
      {hover && (
        <ChartTooltip x={hover.x} y={hover.y - 12}>
          <strong>{dados[hover.idx].bimestre}º bimestre</strong>
          <br />
          {formatarPercentualGrafico(dados[hover.idx].valor)}
        </ChartTooltip>
      )}
    </Paper>
  );
}

interface Coluna<T> {
  chave: keyof T;
  rotulo: string;
  tipo: "percentual" | "moeda" | "texto";
}

interface ConfigIndice<T> {
  titulo: string;
  recurso: string;
  minimoOuMaximoLabel: string;
  colunas: Coluna<T>[];
  campos: CampoEdicao[];
}

function CardStatus<T extends { bimestre: number; percentual_aplicado?: string; cumpre_limite: boolean }>({
  titulo,
  minimoOuMaximoLabel,
  maisRecente,
  percentual,
}: {
  titulo: string;
  minimoOuMaximoLabel: string;
  maisRecente: T | null;
  percentual: number | null;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, minWidth: 200, flex: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {titulo}
      </Typography>
      {maisRecente && percentual !== null ? (
        <>
          <Typography variant="h5" color={maisRecente.cumpre_limite ? "success.main" : "error.main"}>
            {formatarPercentual(percentual)}
          </Typography>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center", mt: 0.5 }}>
            <Chip
              size="small"
              label={maisRecente.cumpre_limite ? "Cumprindo" : "Não cumprindo"}
              color={maisRecente.cumpre_limite ? "success" : "error"}
            />
            <Typography variant="caption" color="text.secondary">
              {minimoOuMaximoLabel} · bim. {maisRecente.bimestre}
            </Typography>
          </Box>
        </>
      ) : (
        <Typography variant="body2" color="text.secondary">
          Sem dados
        </Typography>
      )}
    </Paper>
  );
}

function TabelaIndice<T extends CampoOrigemRegistro & { id: number; bimestre: number; exercicio: number }>({
  config,
  dados,
  municipioSelecionadoId,
  exercicioId,
  onAlterado,
}: {
  config: ConfigIndice<T>;
  dados: T[];
  municipioSelecionadoId: number | null;
  exercicioId: number | "";
  onAlterado: () => void;
}) {
  const [dialogoAberto, setDialogoAberto] = useState(false);
  const [novo, setNovo] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function salvarNovo() {
    setSalvando(true);
    setErro(null);
    try {
      const payload: Record<string, string | number | null> = {
        municipio: municipioSelecionadoId,
        exercicio: novo.exercicio || exercicioId || null,
        bimestre: novo.bimestre,
      };
      for (const c of config.campos) {
        payload[c.chave] = novo[c.chave] || "0";
      }
      await api.post(`/${config.recurso}/`, payload);
      setDialogoAberto(false);
      setNovo({});
      onAlterado();
    } catch {
      setErro("Não foi possível salvar. Confira os campos obrigatórios (Exercício e Bimestre).");
    } finally {
      setSalvando(false);
    }
  }

  const linhasOrdenadas = dados.slice().sort((a, b) => a.bimestre - b.bimestre);

  return (
    <Box sx={{ mb: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h6">{config.titulo}</Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={() => {
            setNovo({ exercicio: exercicioId ? String(exercicioId) : "" });
            setDialogoAberto(true);
          }}
        >
          Novo
        </Button>
      </Box>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Bimestre</TableCell>
              {config.colunas.map((c) => (
                <TableCell key={String(c.chave)} align="right">
                  {c.rotulo}
                </TableCell>
              ))}
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {linhasOrdenadas.length === 0 && (
              <TableRow>
                <TableCell colSpan={config.colunas.length + 2} align="center">
                  Nenhum dado importado para este exercício.
                </TableCell>
              </TableRow>
            )}
            {linhasOrdenadas.map((linha) => (
              <TableRow key={linha.id}>
                <TableCell>{linha.bimestre}</TableCell>
                {config.colunas.map((c) => {
                  const valor = linha[c.chave] as unknown as string | number | null;
                  return (
                    <TableCell key={String(c.chave)} align="right">
                      {valor === null || valor === ""
                        ? "—"
                        : c.tipo === "percentual"
                        ? formatarPercentual(valor)
                        : c.tipo === "texto"
                        ? valor
                        : formatarMoeda(valor)}
                    </TableCell>
                  );
                })}
                <TableCell align="right">
                  <AcoesRegistroManual
                    item={linha}
                    recurso={config.recurso}
                    campos={config.campos}
                    rotuloItem={`${config.titulo} — bimestre ${linha.bimestre}/${linha.exercicio}`}
                    onSalvo={onAlterado}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogoAberto} onClose={() => setDialogoAberto(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Novo — {config.titulo}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {erro && <Alert severity="error">{erro}</Alert>}
          <TextField
            label="Exercício"
            type="number"
            required
            value={novo.exercicio ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, exercicio: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Bimestre (1-6)"
            type="number"
            required
            value={novo.bimestre ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, bimestre: e.target.value }))}
            fullWidth
          />
          {config.campos.map((c) => (
            <TextField
              key={c.chave}
              label={c.rotulo}
              type="number"
              value={novo[c.chave] ?? ""}
              onChange={(e) => setNovo((f) => ({ ...f, [c.chave]: e.target.value }))}
              fullWidth
            />
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogoAberto(false)}>Cancelar</Button>
          <Button variant="contained" disabled={salvando} onClick={salvarNovo}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

const CONFIG_DTP: ConfigIndice<ApuracaoDTP> = {
  titulo: "DTP — Despesa Total com Pessoal (máx. 54%)",
  recurso: "apuracao-dtp",
  minimoOuMaximoLabel: "máx. 54%",
  colunas: [
    { chave: "rcl_ajustada", rotulo: "RCL Ajustada", tipo: "moeda" },
    { chave: "despesa_total_pessoal", rotulo: "DTP", tipo: "moeda" },
    { chave: "percentual_dtp", rotulo: "% DTP", tipo: "percentual" },
    { chave: "limite_maximo_percentual", rotulo: "Limite Máx. (%)", tipo: "percentual" },
  ],
  campos: [
    { chave: "rcl", rotulo: "RCL", tipo: "decimal" },
    { chave: "deducao_emendas_individuais", rotulo: "Dedução — Emendas Individuais", tipo: "decimal" },
    { chave: "deducao_emendas_bancada", rotulo: "Dedução — Emendas de Bancada", tipo: "decimal" },
    { chave: "deducao_agentes_saude", rotulo: "Dedução — Agentes Comunitários de Saúde", tipo: "decimal" },
    { chave: "deducao_outras", rotulo: "Outras Deduções", tipo: "decimal" },
    { chave: "rcl_ajustada", rotulo: "RCL Ajustada", tipo: "decimal" },
    { chave: "despesa_total_pessoal", rotulo: "Despesa Total com Pessoal", tipo: "decimal" },
    { chave: "percentual_dtp", rotulo: "% DTP", tipo: "decimal" },
    { chave: "limite_maximo_valor", rotulo: "Limite Máximo (valor)", tipo: "decimal" },
    { chave: "limite_maximo_percentual", rotulo: "Limite Máximo (%)", tipo: "decimal" },
    { chave: "limite_prudencial_valor", rotulo: "Limite Prudencial (valor)", tipo: "decimal" },
    { chave: "limite_prudencial_percentual", rotulo: "Limite Prudencial (%)", tipo: "decimal" },
    { chave: "limite_alerta_valor", rotulo: "Limite de Alerta (valor)", tipo: "decimal" },
    { chave: "limite_alerta_percentual", rotulo: "Limite de Alerta (%)", tipo: "decimal" },
  ],
};

const CONFIG_MDE: ConfigIndice<ApuracaoMDE> = {
  titulo: "MDE — Manutenção e Desenvolvimento do Ensino (mín. 25%)",
  recurso: "apuracao-mde",
  minimoOuMaximoLabel: "mín. 25%",
  colunas: [
    { chave: "base_calculo", rotulo: "Base de Cálculo", tipo: "moeda" },
    { chave: "despesa_mde_liquidada", rotulo: "Despesa MDE", tipo: "moeda" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "moeda" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "percentual" },
  ],
  campos: CAMPOS_MDE,
};

const CONFIG_MAGISTERIO: ConfigIndice<ApuracaoMagisterioFundeb> = {
  titulo: "Magistério/FUNDEB (mín. 70%)",
  recurso: "apuracao-magisterio-fundeb",
  minimoOuMaximoLabel: "mín. 70%",
  colunas: [
    { chave: "fundeb_receita_total", rotulo: "Receita Total FUNDEB", tipo: "moeda" },
    { chave: "valor_exigido", rotulo: "Valor Exigido (70%)", tipo: "moeda" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "moeda" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "percentual" },
  ],
  campos: [
    { chave: "fundeb_receita_total", rotulo: "Receita Total FUNDEB", tipo: "decimal" },
    { chave: "valor_exigido", rotulo: "Valor Exigido (70%)", tipo: "decimal" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "decimal" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "decimal" },
  ],
};

const CONFIG_ETI: ConfigIndice<ApuracaoETIFundeb> = {
  titulo: "FUNDEB — Mínimo de 4% em Matrículas ETI",
  recurso: "apuracao-fundeb-eti",
  minimoOuMaximoLabel: "mín. 4%",
  colunas: [
    { chave: "fundeb_receita_total", rotulo: "Receita Total FUNDEB", tipo: "moeda" },
    { chave: "valor_exigido", rotulo: "Valor Exigido (4%)", tipo: "moeda" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "moeda" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "percentual" },
  ],
  campos: [
    { chave: "fundeb_receita_total", rotulo: "Receita Total FUNDEB", tipo: "decimal" },
    { chave: "valor_exigido", rotulo: "Valor Exigido (4%)", tipo: "decimal" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "decimal" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "decimal" },
  ],
};

const CONFIG_ASPS: ConfigIndice<ApuracaoASPS> = {
  titulo: "ASPS — Ações e Serviços Públicos de Saúde (mín. 15%)",
  recurso: "apuracao-asps",
  minimoOuMaximoLabel: "mín. 15%",
  colunas: [
    { chave: "base_calculo", rotulo: "Base de Cálculo", tipo: "moeda" },
    { chave: "despesa_asps_liquidada", rotulo: "Despesa ASPS", tipo: "moeda" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "percentual" },
  ],
  campos: [
    { chave: "receita_impostos_transferencias", rotulo: "Receita de Impostos/Transferências", tipo: "decimal" },
    { chave: "base_calculo", rotulo: "Base de Cálculo", tipo: "decimal" },
    { chave: "minimo_constitucional", rotulo: "Mínimo Constitucional (15%)", tipo: "decimal" },
    { chave: "despesa_asps_empenhada", rotulo: "Despesa ASPS Empenhada", tipo: "decimal" },
    { chave: "despesa_asps_liquidada", rotulo: "Despesa ASPS Liquidada", tipo: "decimal" },
    { chave: "despesa_asps_paga", rotulo: "Despesa ASPS Paga", tipo: "decimal" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado (ÍNDICE STN)", tipo: "decimal" },
  ],
};

const CONFIG_VAAT_EDUCACAO_INFANTIL: ConfigIndice<ApuracaoVAATEducacaoInfantil> = {
  titulo: "VAAT — Aplicação em Educação Infantil",
  recurso: "apuracao-vaat-educacao-infantil",
  minimoOuMaximoLabel: "conforme valor exigido",
  colunas: [
    { chave: "valor_exigido", rotulo: "Valor Exigido", tipo: "moeda" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "moeda" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "percentual" },
    { chave: "percentual_vaat_publicado", rotulo: "% VAAT Publicado (MEC/MF)", tipo: "percentual" },
    { chave: "portaria_vaat_referencia", rotulo: "Portaria de Referência", tipo: "texto" },
  ],
  campos: [
    { chave: "valor_exigido", rotulo: "Valor Exigido", tipo: "decimal" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "decimal" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "decimal" },
    { chave: "percentual_vaat_publicado", rotulo: "% VAAT Publicado (MEC/MF)", tipo: "decimal" },
    { chave: "portaria_vaat_referencia", rotulo: "Portaria de Referência (ex.: Portaria MEC/MF nº 6, de 29/04/2026)", tipo: "texto" },
  ],
};

const CONFIG_VAAT_DESPESA_CAPITAL: ConfigIndice<ApuracaoVAATDespesaCapital> = {
  titulo: "VAAT — Despesa de Capital (mín. 15%)",
  recurso: "apuracao-vaat-despesa-capital",
  minimoOuMaximoLabel: "mín. 15%",
  colunas: [
    { chave: "valor_exigido", rotulo: "Valor Exigido (15%)", tipo: "moeda" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "moeda" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "percentual" },
  ],
  campos: [
    { chave: "valor_exigido", rotulo: "Valor Exigido (15%)", tipo: "decimal" },
    { chave: "valor_aplicado", rotulo: "Valor Aplicado", tipo: "decimal" },
    { chave: "percentual_aplicado", rotulo: "% Aplicado", tipo: "decimal" },
  ],
};

const CONFIG_FUNDEB_NAO_APLICADO: ConfigIndice<ApuracaoValorNaoAplicadoFundeb> = {
  titulo: "FUNDEB — Valor Não Aplicado (máx. 10% de superávit)",
  recurso: "apuracao-fundeb-nao-aplicado",
  minimoOuMaximoLabel: "sem excedente ao máximo permitido",
  colunas: [
    { chave: "valor_maximo_permitido", rotulo: "Máx. Permitido (10%)", tipo: "moeda" },
    { chave: "valor_nao_aplicado", rotulo: "Valor Não Aplicado", tipo: "moeda" },
    { chave: "valor_excedente_ao_maximo_permitido", rotulo: "Excedente ao Máximo", tipo: "moeda" },
    { chave: "percentual_nao_aplicado", rotulo: "% Não Aplicado", tipo: "percentual" },
  ],
  campos: [
    { chave: "valor_maximo_permitido", rotulo: "Valor Máximo Permitido (10% de Superávit)", tipo: "decimal" },
    { chave: "valor_nao_aplicado", rotulo: "Valor Não Aplicado", tipo: "decimal" },
    { chave: "valor_nao_aplicado_apos_ajuste", rotulo: "Valor Não Aplicado Após Ajuste", tipo: "decimal" },
    { chave: "valor_excedente_ao_maximo_permitido", rotulo: "Valor Excedente ao Máximo Permitido", tipo: "decimal" },
    { chave: "percentual_nao_aplicado", rotulo: "% Não Aplicado", tipo: "decimal" },
  ],
};

// `mostrarEmpenhado` alterna as 2 colunas de "aplicado" entre a visão
// oficial (liquidado — a mesma base do "aplicado até o 1º quadrimestre"
// que o próprio RREO-Anexo 8 já reporta certo) e a visão GERENCIAL
// (empenhado), pedida pelo usuário ("fazer igual ao MDE e ter o cálculo
// gerencial informado também o valor empenhado" + "um botão, considerar
// despesa empenhada"). `campos` (edição) sempre lista os 4 campos — o
// toggle só afeta quais 2 aparecem como coluna da tabela.
function construirConfigReprogramacao(mostrarEmpenhado: boolean): ConfigIndice<ApuracaoReprogramacaoFundeb> {
  const sufixo = mostrarEmpenhado ? "_empenhado" : "";
  const rotuloSufixo = mostrarEmpenhado ? " (Gerencial — Empenhado)" : "";
  return {
    titulo: "FUNDEB — Reprogramação (Superávit do Exercício Anterior)",
    recurso: "apuracao-fundeb-reprogramacao",
    minimoOuMaximoLabel: "integralmente aplicado até o 1º quadrimestre",
    colunas: [
      { chave: "valor_superavit_permitido_exercicio_anterior", rotulo: "Superávit Permitido (Exerc. Anterior)", tipo: "moeda" },
      {
        chave: `valor_aplicado_ate_primeiro_quadrimestre${sufixo}` as keyof ApuracaoReprogramacaoFundeb,
        rotulo: `Aplicado até o 1º Quadrimestre${rotuloSufixo}`,
        tipo: "moeda",
      },
      {
        chave: `valor_aplicado_apos_primeiro_quadrimestre${sufixo}` as keyof ApuracaoReprogramacaoFundeb,
        rotulo: `Aplicado Após o 1º Quadrimestre${rotuloSufixo}`,
        tipo: "moeda",
      },
      {
        chave: "valor_nao_aplicado_ate_primeiro_quadrimestre_atual",
        rotulo: "Saldo a Aplicar (até o 1º Quadrimestre Atual)",
        tipo: "moeda",
      },
    ],
    campos: [
      { chave: "valor_superavit_permitido_exercicio_anterior", rotulo: "Valor Superávit Permitido (Exerc. Anterior)", tipo: "decimal" },
      { chave: "valor_nao_aplicado_exercicio_anterior", rotulo: "Valor Não Aplicado (Exerc. Anterior)", tipo: "decimal" },
      { chave: "valor_aplicado_ate_primeiro_quadrimestre", rotulo: "Valor Aplicado até o 1º Quadrimestre (Oficial — Liquidado)", tipo: "decimal" },
      { chave: "valor_aplicado_apos_primeiro_quadrimestre", rotulo: "Valor Aplicado Após o 1º Quadrimestre (Oficial — Liquidado)", tipo: "decimal" },
      { chave: "valor_aplicado_ate_primeiro_quadrimestre_empenhado", rotulo: "Valor Aplicado até o 1º Quadrimestre (Gerencial — Empenhado)", tipo: "decimal" },
      { chave: "valor_aplicado_apos_primeiro_quadrimestre_empenhado", rotulo: "Valor Aplicado Após o 1º Quadrimestre (Gerencial — Empenhado)", tipo: "decimal" },
      {
        chave: "valor_nao_aplicado_ate_primeiro_quadrimestre_atual",
        rotulo: "Saldo a Aplicar (Não Aplicado) até o 1º Quadrimestre Atual",
        tipo: "decimal",
      },
      // A quebra por origem (19.1 impostos / 19.2 União) não é mais editável
      // aqui — mora em `ApuracaoReprogramacaoFundebOrigem` (tabela filha,
      // somente leitura via API, populada só pelo import). Ver essa
      // composição na visão detalhada (`ExecucaoFiscalDetalhadoPage.tsx`).
    ],
  };
}

// `tabela` usa `any` deliberadamente: cada item carrega seu próprio par
// config/dados sempre correlacionado (nunca misturado entre índices), mas
// TypeScript não consegue provar essa correlação para um único T genérico
// quando os 9 itens vêm de uma união de tipos distintos — `any` aqui é só
// a ponte de tipo no limite com o componente genérico `TabelaIndice`, os
// valores em si continuam corretos em runtime.
interface ItemIndice {
  chave: string;
  tituloMenu: string;
  card: {
    titulo: string;
    minimoOuMaximoLabel: string;
    maisRecente: { bimestre: number; percentual_aplicado?: string; cumpre_limite: boolean } | null;
    percentual: number | null;
  } | null;
  grafico: { titulo: string; dados: PontoBarraLimite[]; linhas: LinhaLimite[] } | null;
  tabela: { config: ConfigIndice<any>; dados: any[] };
}

export function ExecucaoFiscalPage() {
  const navigate = useNavigate();
  const { municipioSelecionadoId } = useScope();
  const exibirAvisos = useParametro("exibir_avisos_informativos");
  const theme = useTheme();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [indiceSelecionado, setIndiceSelecionado] = useState("dtp");
  const [reprogramacaoEmpenhado, setReprogramacaoEmpenhado] = useState(false);

  const [dtp, setDtp] = useState<ApuracaoDTP[]>([]);
  const [mde, setMde] = useState<ApuracaoMDE[]>([]);
  const [magisterio, setMagisterio] = useState<ApuracaoMagisterioFundeb[]>([]);
  const [eti, setEti] = useState<ApuracaoETIFundeb[]>([]);
  const [asps, setAsps] = useState<ApuracaoASPS[]>([]);
  const [vaatEdInfantil, setVaatEdInfantil] = useState<ApuracaoVAATEducacaoInfantil[]>([]);
  const [vaatCapital, setVaatCapital] = useState<ApuracaoVAATDespesaCapital[]>([]);
  const [fundebNaoAplicado, setFundebNaoAplicado] = useState<ApuracaoValorNaoAplicadoFundeb[]>([]);
  const [fundebReprogramacao, setFundebReprogramacao] = useState<ApuracaoReprogramacaoFundeb[]>([]);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        setExercicios(data.results);
        setExercicioId(data.results[0]?.id ?? "");
      });
  }, [municipioSelecionadoId]);

  const exercicioSelecionado = useMemo(
    () => exercicios.find((e) => e.id === exercicioId) ?? null,
    [exercicios, exercicioId]
  );

  function recarregar() {
    if (!municipioSelecionadoId || !exercicioSelecionado) return;
    const params = { municipio: municipioSelecionadoId, exercicio: exercicioSelecionado.ano };
    buscarTodasPaginas<ApuracaoDTP>("/apuracao-dtp/", params).then(setDtp);
    buscarTodasPaginas<ApuracaoMDE>("/apuracao-mde/", params).then(setMde);
    buscarTodasPaginas<ApuracaoMagisterioFundeb>("/apuracao-magisterio-fundeb/", params).then(setMagisterio);
    buscarTodasPaginas<ApuracaoETIFundeb>("/apuracao-fundeb-eti/", params).then(setEti);
    buscarTodasPaginas<ApuracaoASPS>("/apuracao-asps/", params).then(setAsps);
    buscarTodasPaginas<ApuracaoVAATEducacaoInfantil>("/apuracao-vaat-educacao-infantil/", params).then(setVaatEdInfantil);
    buscarTodasPaginas<ApuracaoVAATDespesaCapital>("/apuracao-vaat-despesa-capital/", params).then(setVaatCapital);
    buscarTodasPaginas<ApuracaoValorNaoAplicadoFundeb>("/apuracao-fundeb-nao-aplicado/", params).then(setFundebNaoAplicado);
    buscarTodasPaginas<ApuracaoReprogramacaoFundeb>("/apuracao-fundeb-reprogramacao/", params).then(setFundebReprogramacao);
  }

  useEffect(() => {
    recarregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [municipioSelecionadoId, exercicioSelecionado]);

  const dtpRecente = dtp.length ? dtp.slice().sort((a, b) => b.bimestre - a.bimestre)[0] : null;
  const mdeRecente = mde.length ? mde.slice().sort((a, b) => b.bimestre - a.bimestre)[0] : null;
  const magisterioRecente = magisterio.length ? magisterio.slice().sort((a, b) => b.bimestre - a.bimestre)[0] : null;
  const etiRecente = eti.length ? eti.slice().sort((a, b) => b.bimestre - a.bimestre)[0] : null;
  const aspsRecente = asps.length ? asps.slice().sort((a, b) => b.bimestre - a.bimestre)[0] : null;
  const vaatEdInfantilRecente = vaatEdInfantil.length
    ? vaatEdInfantil.slice().sort((a, b) => b.bimestre - a.bimestre)[0]
    : null;
  const vaatCapitalRecente = vaatCapital.length
    ? vaatCapital.slice().sort((a, b) => b.bimestre - a.bimestre)[0]
    : null;
  const fundebNaoAplicadoRecente = fundebNaoAplicado.length
    ? fundebNaoAplicado.slice().sort((a, b) => b.bimestre - a.bimestre)[0]
    : null;

  // Um item por índice — card+gráfico+tabela sempre vêm juntos do mesmo
  // objeto (nunca combinados entre índices diferentes), então o generic de
  // TabelaIndice infere T corretamente mesmo com o array sendo uma união de
  // 9 formas. Reprogramação não tem card/gráfico (o relatório não traz um
  // percentual pra ela, só valores monetários) — ver Alert abaixo.
  const itens: ItemIndice[] = [
    {
      chave: "dtp", tituloMenu: "DTP — Despesa Total com Pessoal",
      card: { titulo: "DTP", minimoOuMaximoLabel: "máx. 54%", maisRecente: dtpRecente, percentual: dtpRecente ? Number(dtpRecente.percentual_dtp) : null },
      grafico: {
        titulo: "DTP por bimestre (%)",
        dados: paraBarraLimite(dtp, (d) => Number(d.percentual_dtp)),
        // DTP é o único índice com 3 limiares reais (não só o teto) — lidos
        // do próprio dado (bimestre mais recente), não hardcoded, já que o
        // RGF já calcula os 3 a partir da RCL Ajustada daquele bimestre.
        linhas: dtpRecente
          ? [
              { valor: Number(dtpRecente.limite_alerta_percentual), rotulo: `Alerta ${formatarPercentualGrafico(Number(dtpRecente.limite_alerta_percentual))}`, cor: "#eda100" },
              { valor: Number(dtpRecente.limite_prudencial_percentual), rotulo: `Prudencial ${formatarPercentualGrafico(Number(dtpRecente.limite_prudencial_percentual))}`, cor: "#eb6834" },
              { valor: Number(dtpRecente.limite_maximo_percentual), rotulo: `Máximo ${formatarPercentualGrafico(Number(dtpRecente.limite_maximo_percentual))}`, cor: theme.palette.error.main },
            ]
          : [],
      },
      tabela: { config: CONFIG_DTP, dados: dtp },
    },
    {
      chave: "mde", tituloMenu: "MDE — Manutenção e Desenvolvimento do Ensino",
      card: { titulo: "MDE", minimoOuMaximoLabel: "mín. 25%", maisRecente: mdeRecente, percentual: mdeRecente ? Number(mdeRecente.percentual_aplicado) : null },
      grafico: { titulo: "MDE por bimestre (%)", dados: paraBarraLimite(mde, (d) => Number(d.percentual_aplicado)), linhas: linhaUnica("mín. 25%") },
      tabela: { config: CONFIG_MDE, dados: mde },
    },
    {
      chave: "magisterio", tituloMenu: "Magistério/FUNDEB",
      card: { titulo: "Magistério/FUNDEB", minimoOuMaximoLabel: "mín. 70%", maisRecente: magisterioRecente, percentual: magisterioRecente ? Number(magisterioRecente.percentual_aplicado) : null },
      grafico: { titulo: "Magistério/FUNDEB por bimestre (%)", dados: paraBarraLimite(magisterio, (d) => Number(d.percentual_aplicado)), linhas: linhaUnica("mín. 70%") },
      tabela: { config: CONFIG_MAGISTERIO, dados: magisterio },
    },
    {
      chave: "eti", tituloMenu: "FUNDEB — Mínimo de 4% em Matrículas ETI",
      card: { titulo: "FUNDEB ETI", minimoOuMaximoLabel: "mín. 4%", maisRecente: etiRecente, percentual: etiRecente ? Number(etiRecente.percentual_aplicado) : null },
      grafico: { titulo: "FUNDEB ETI por bimestre (%)", dados: paraBarraLimite(eti, (d) => Number(d.percentual_aplicado)), linhas: linhaUnica("mín. 4%") },
      tabela: { config: CONFIG_ETI, dados: eti },
    },
    {
      chave: "asps", tituloMenu: "ASPS — Ações e Serviços Públicos de Saúde",
      card: { titulo: "ASPS", minimoOuMaximoLabel: "mín. 15%", maisRecente: aspsRecente, percentual: aspsRecente ? Number(aspsRecente.percentual_aplicado) : null },
      grafico: { titulo: "ASPS por bimestre (%)", dados: paraBarraLimite(asps, (d) => Number(d.percentual_aplicado)), linhas: linhaUnica("mín. 15%") },
      tabela: { config: CONFIG_ASPS, dados: asps },
    },
    {
      chave: "vaat_ed_infantil", tituloMenu: "VAAT — Educação Infantil",
      card: { titulo: "VAAT Educação Infantil", minimoOuMaximoLabel: "conforme valor exigido", maisRecente: vaatEdInfantilRecente, percentual: vaatEdInfantilRecente ? Number(vaatEdInfantilRecente.percentual_aplicado) : null },
      grafico: {
        titulo: "VAAT Educação Infantil por bimestre (%)",
        dados: paraBarraLimite(vaatEdInfantil, (d) => Number(d.percentual_aplicado)),
        linhas: linhaVariavelPorBimestre(
          vaatEdInfantil, (d) => d.percentual_vaat_publicado, "% VAAT Publicado (MEC/MF)", AZUL_SEQUENCIAL
        ),
      },
      tabela: { config: CONFIG_VAAT_EDUCACAO_INFANTIL, dados: vaatEdInfantil },
    },
    {
      chave: "vaat_capital", tituloMenu: "VAAT — Despesa de Capital",
      card: { titulo: "VAAT Despesa de Capital", minimoOuMaximoLabel: "mín. 15%", maisRecente: vaatCapitalRecente, percentual: vaatCapitalRecente ? Number(vaatCapitalRecente.percentual_aplicado) : null },
      grafico: { titulo: "VAAT Despesa de Capital por bimestre (%)", dados: paraBarraLimite(vaatCapital, (d) => Number(d.percentual_aplicado)), linhas: linhaUnica("mín. 15%") },
      tabela: { config: CONFIG_VAAT_DESPESA_CAPITAL, dados: vaatCapital },
    },
    {
      chave: "fundeb_nao_aplicado", tituloMenu: "FUNDEB — Valor Não Aplicado",
      card: { titulo: "FUNDEB Não Aplicado", minimoOuMaximoLabel: "sem excedente ao máx. de 10%", maisRecente: fundebNaoAplicadoRecente, percentual: fundebNaoAplicadoRecente ? Number(fundebNaoAplicadoRecente.percentual_nao_aplicado) : null },
      grafico: { titulo: "FUNDEB Não Aplicado por bimestre (%)", dados: paraBarraLimite(fundebNaoAplicado, (d) => Number(d.percentual_nao_aplicado)), linhas: linhaUnica("máx. 10%") },
      tabela: { config: CONFIG_FUNDEB_NAO_APLICADO, dados: fundebNaoAplicado },
    },
    {
      chave: "fundeb_reprogramacao", tituloMenu: "FUNDEB — Reprogramação",
      card: null,
      grafico: null,
      tabela: { config: construirConfigReprogramacao(reprogramacaoEmpenhado), dados: fundebReprogramacao },
    },
  ];

  const itemSelecionado = itens.find((i) => i.chave === indiceSelecionado) ?? itens[0];

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 2 }}>
        <Typography variant="h5" gutterBottom>
          Execução Fiscal — Índices Constitucionais
        </Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<SummarizeIcon />}
            onClick={() =>
              navigate(`/execucao-fiscal/resumo${exercicioSelecionado ? `?exercicio=${exercicioSelecionado.ano}` : ""}`)
            }
          >
            Ver Resumo Geral
          </Button>
          <Button
            variant="outlined"
            startIcon={<TableChartIcon />}
            onClick={() =>
              navigate(`/execucao-fiscal/detalhado${exercicioSelecionado ? `?exercicio=${exercicioSelecionado.ano}` : ""}`)
            }
          >
            Ver Detalhado
          </Button>
        </Box>
      </Box>
      {exibirAvisos && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Acompanhamento de 9 índices fiscais constitucionais/LRF apurados por bimestre, a partir do RGF-Anexo 1 e
          RREO-Anexos 8/XII. Selecione o exercício e o índice abaixo — a Reprogramação do FUNDEB não tem card/gráfico
          próprio (o relatório não traz um percentual para ela, só valores monetários), apenas tabela com CRUD.
        </Alert>
      )}

      <Box sx={{ display: "flex", gap: 2, mb: 4, flexWrap: "wrap" }}>
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
        <Select
          size="small"
          value={indiceSelecionado}
          onChange={(e) => setIndiceSelecionado(e.target.value)}
          sx={{ minWidth: 260 }}
        >
          {itens.map((item) => (
            <MenuItem key={item.chave} value={item.chave}>
              {item.tituloMenu}
            </MenuItem>
          ))}
        </Select>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "flex-start" }}>
        {itemSelecionado.card && (
          <Box sx={{ width: 260, flexShrink: 0 }}>
            <CardStatus
              titulo={itemSelecionado.card.titulo}
              minimoOuMaximoLabel={itemSelecionado.card.minimoOuMaximoLabel}
              maisRecente={itemSelecionado.card.maisRecente}
              percentual={itemSelecionado.card.percentual}
            />
          </Box>
        )}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {itemSelecionado.chave === "fundeb_reprogramacao" && (
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
          )}
          <TabelaIndice
            config={itemSelecionado.tabela.config}
            dados={itemSelecionado.tabela.dados}
            municipioSelecionadoId={municipioSelecionadoId}
            exercicioId={exercicioSelecionado?.ano ?? ""}
            onAlterado={recarregar}
          />
        </Box>
      </Box>

      {itemSelecionado.grafico && (
        <GraficoBarraLimite
          titulo={itemSelecionado.grafico.titulo}
          dados={itemSelecionado.grafico.dados}
          linhas={itemSelecionado.grafico.linhas}
        />
      )}
    </Box>
  );
}
