import { useState } from "react";
import { Box, Paper, Typography } from "@mui/material";

// Extraído de RelatorioExecucaoPage.tsx (onde foi criado e validado contra a
// paleta do skill dataviz) para ser reaproveitado por qualquer página que
// precise de um gráfico de linha com tendência mensal — ver
// RelatorioFinanceiroPage.tsx para o segundo uso.

export const MESES_ABREV = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

// paleta validada (dataviz skill) — node scripts/validate_palette.js
// "#2a78d6,#eb6834,#1baf7a,#eda100" --mode light => PASS
export const AZUL_SEQUENCIAL = "#2a78d6";
export const INK_MUTED = "#898781";
export const GRID_LINE = "#e1e0d9";
export const SURFACE = "#fcfcfb";

export function formatarMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatarCompacto(valor: number): string {
  if (Math.abs(valor) >= 1_000_000) return `R$ ${(valor / 1_000_000).toFixed(1)}M`;
  if (Math.abs(valor) >= 1_000) return `R$ ${(valor / 1_000).toFixed(1)}K`;
  return formatarMoeda(valor);
}

export function ChartTooltip({ x, y, children }: { x: number; y: number; children: React.ReactNode }) {
  return (
    <Paper
      elevation={3}
      sx={{
        position: "absolute",
        left: x,
        top: y,
        transform: "translate(-50%, -100%)",
        p: "6px 10px",
        pointerEvents: "none",
        whiteSpace: "nowrap",
        fontSize: "0.75rem",
        zIndex: 10,
      }}
    >
      {children}
    </Paper>
  );
}

export interface PontoTendencia {
  mes: number;
  valor: number;
}

export function GraficoLinhaTendencia({
  titulo,
  dados,
  formatarValor = formatarCompacto,
  formatarValorTooltip = formatarMoeda,
}: {
  titulo: string;
  dados: PontoTendencia[];
  /** Formata os rótulos do eixo Y — default assume dinheiro (R$); passe um formatador próprio para outras unidades (ex.: "%"). */
  formatarValor?: (valor: number) => string;
  /** Formata o valor exato mostrado no tooltip ao passar o mouse — default também assume dinheiro. */
  formatarValorTooltip?: (valor: number) => string;
}) {
  const [hover, setHover] = useState<{ x: number; y: number; idx: number } | null>(null);
  const largura = 600;
  const altura = 220;
  const margem = { top: 16, right: 16, bottom: 28, left: 70 };
  const plotW = largura - margem.left - margem.right;
  const plotH = altura - margem.top - margem.bottom;

  if (dados.length === 0) {
    return (
      <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 320 }}>
        <Typography variant="subtitle2" gutterBottom>{titulo}</Typography>
        <Typography variant="body2" color="text.secondary">Sem dados para o período.</Typography>
      </Paper>
    );
  }

  // minValor <= 0 sempre, para a linha de base (0) aparecer mesmo quando
  // toda a série é positiva — e a série poder ir negativa (ex.:
  // Disponibilidade Líquida) sem os pontos vazarem para fora do gráfico.
  const minValor = Math.min(0, ...dados.map((d) => d.valor));
  const maxValor = Math.max(1, ...dados.map((d) => d.valor));
  const amplitude = maxValor - minValor || 1;
  const escalaY = (v: number) => margem.top + plotH - ((v - minValor) / amplitude) * plotH;
  const escalaX = (i: number) => margem.left + (dados.length === 1 ? plotW / 2 : (i / (dados.length - 1)) * plotW);

  const pontos = dados.map((d, i) => ({ x: escalaX(i), y: escalaY(d.valor), ...d }));
  const linha = pontos.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const yBase = escalaY(0);
  const area = `${linha} L${pontos[pontos.length - 1].x},${yBase} L${pontos[0].x},${yBase} Z`;

  const passos = 4;
  const gridY = Array.from({ length: passos + 1 }, (_, i) => margem.top + (plotH / passos) * i);

  return (
    <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 320, position: "relative" }}>
      <Typography variant="subtitle2" gutterBottom>{titulo}</Typography>
      <Box sx={{ position: "relative" }}>
        <svg viewBox={`0 0 ${largura} ${altura}`} style={{ width: "100%", height: "auto", display: "block" }}>
          {gridY.map((y, i) => (
            <g key={i}>
              <line x1={margem.left} y1={y} x2={largura - margem.right} y2={y} stroke={GRID_LINE} strokeWidth={1} />
              <text x={margem.left - 8} y={y} textAnchor="end" dominantBaseline="middle" fontSize={10} fill={INK_MUTED}>
                {formatarValor(maxValor - (amplitude / passos) * i)}
              </text>
            </g>
          ))}
          {minValor < 0 && (
            <line x1={margem.left} y1={yBase} x2={largura - margem.right} y2={yBase} stroke={INK_MUTED} strokeWidth={1} />
          )}
          <path d={area} fill={AZUL_SEQUENCIAL} opacity={0.1} />
          <path d={linha} fill="none" stroke={AZUL_SEQUENCIAL} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {pontos.map((p, i) => (
            <g key={i}>
              <circle
                cx={p.x} cy={p.y} r={4}
                fill={AZUL_SEQUENCIAL} stroke={SURFACE} strokeWidth={2}
                onMouseEnter={(e) => setHover({ x: e.clientX, y: e.clientY, idx: i })}
                onMouseMove={(e) => setHover({ x: e.clientX, y: e.clientY, idx: i })}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: "pointer" }}
              />
              <text x={p.x} y={altura - margem.bottom + 16} textAnchor="middle" fontSize={10} fill={INK_MUTED}>
                {MESES_ABREV[p.mes - 1].slice(0, 3)}
              </text>
            </g>
          ))}
          {hover && (
            <line
              x1={pontos[hover.idx].x} y1={margem.top}
              x2={pontos[hover.idx].x} y2={margem.top + plotH}
              stroke={GRID_LINE} strokeWidth={1}
            />
          )}
        </svg>
      </Box>
      {hover && (
        <ChartTooltip x={hover.x} y={hover.y - 12}>
          <strong>{MESES_ABREV[pontos[hover.idx].mes - 1]}</strong>
          <br />
          {formatarValorTooltip(pontos[hover.idx].valor)}
        </ChartTooltip>
      )}
    </Paper>
  );
}
