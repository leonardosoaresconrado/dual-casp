import { useState } from "react";
import { Box, Paper, Typography } from "@mui/material";
import { ChartTooltip, formatarCompacto, formatarMoeda, GRID_LINE, INK_MUTED } from "./GraficoLinhaTendencia";

// Extraído de RelatorioExecucaoPage.tsx (onde foi criado e validado contra a
// paleta do skill dataviz) para ser reaproveitado por qualquer página que
// precise de um gráfico de barras horizontais — ver RelatorioReceitaPage.tsx
// para o segundo uso.

const INK_SECONDARY = "#52514e";

function caminhoBarraArredondada(x: number, y: number, largura: number, altura: number, raio: number): string {
  const r = Math.min(raio, largura / 2, altura / 2);
  if (largura <= 0) return "";
  if (r <= 0) return `M${x},${y} h${largura} v${altura} h${-largura} Z`;
  return [
    `M${x},${y}`,
    `h${largura - r}`,
    `a${r},${r} 0 0 1 ${r},${r}`,
    `v${altura - 2 * r}`,
    `a${r},${r} 0 0 1 ${-r},${r}`,
    `h${-(largura - r)}`,
    "Z",
  ].join(" ");
}

export interface BarraDado {
  chave: string;
  rotulo: string;
  valor: number;
  cor: string;
}

export function GraficoBarrasHorizontais({
  titulo,
  dados,
  comSwatch = false,
}: {
  titulo: string;
  dados: BarraDado[];
  comSwatch?: boolean;
}) {
  const [hover, setHover] = useState<{ x: number; y: number; chave: string } | null>(null);
  const alturaBarra = 22;
  const gap = 12;
  const margemEsquerda = 190;
  const margemDireita = 90;
  const largura = 600;
  const alturaGrafico = dados.length * (alturaBarra + gap) + gap;
  const maxValor = Math.max(1, ...dados.map((d) => d.valor));
  const larguraPlot = largura - margemEsquerda - margemDireita;

  if (dados.length === 0) {
    return (
      <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 320 }}>
        <Typography variant="subtitle2" gutterBottom>{titulo}</Typography>
        <Typography variant="body2" color="text.secondary">Sem dados para o período.</Typography>
      </Paper>
    );
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 320, position: "relative" }}>
      <Typography variant="subtitle2" gutterBottom>{titulo}</Typography>
      <Box sx={{ position: "relative" }}>
        <svg viewBox={`0 0 ${largura} ${alturaGrafico}`} style={{ width: "100%", height: "auto", display: "block" }}>
          <line
            x1={margemEsquerda} y1={0} x2={margemEsquerda} y2={alturaGrafico}
            stroke={GRID_LINE} strokeWidth={1}
          />
          {dados.map((d, i) => {
            const y = gap + i * (alturaBarra + gap);
            const w = (d.valor / maxValor) * larguraPlot;
            const destacado = hover?.chave === d.chave;
            return (
              <g key={d.chave}>
                <text
                  x={margemEsquerda - 10}
                  y={y + alturaBarra / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={11}
                  fill={INK_SECONDARY}
                >
                  {comSwatch && (
                    <title>{d.rotulo}</title>
                  )}
                  {d.rotulo.length > 26 ? `${d.rotulo.slice(0, 25)}…` : d.rotulo}
                </text>
                {comSwatch && (
                  <rect x={margemEsquerda - 150} y={y + alturaBarra / 2 - 5} width={10} height={10} rx={2} fill={d.cor} />
                )}
                <path
                  d={caminhoBarraArredondada(margemEsquerda, y, Math.max(w, 2), alturaBarra, 4)}
                  fill={d.cor}
                  opacity={destacado ? 1 : 0.92}
                  onMouseEnter={(e) =>
                    setHover({ x: e.clientX, y: e.clientY, chave: d.chave })
                  }
                  onMouseMove={(e) => setHover({ x: e.clientX, y: e.clientY, chave: d.chave })}
                  onMouseLeave={() => setHover(null)}
                  style={{ cursor: "pointer" }}
                />
                <text
                  x={margemEsquerda + w + 8}
                  y={y + alturaBarra / 2}
                  dominantBaseline="middle"
                  fontSize={11}
                  fill={INK_MUTED}
                >
                  {formatarCompacto(d.valor)}
                </text>
              </g>
            );
          })}
        </svg>
      </Box>
      {hover &&
        (() => {
          const d = dados.find((item) => item.chave === hover.chave);
          if (!d) return null;
          return (
            <ChartTooltip x={hover.x} y={hover.y - 12}>
              <strong>{d.rotulo}</strong>
              <br />
              {formatarMoeda(d.valor)}
            </ChartTooltip>
          );
        })()}
    </Paper>
  );
}
