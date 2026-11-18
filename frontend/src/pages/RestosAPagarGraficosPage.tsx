import { useEffect, useMemo, useState } from "react";
import { Box, Button, MenuItem, Paper, Select, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";
import { buscarTodasPaginas } from "../api/client";
import type { RestoAPagar } from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { AZUL_SEQUENCIAL, GraficoLinhaTendencia, type PontoTendencia } from "../components/charts/GraficoLinhaTendencia";
import { GraficoBarrasHorizontais, type BarraDado } from "../components/charts/GraficoBarrasHorizontais";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

// Mesma fórmula de RestosAPagarPage.tsx — tudo que foi inscrito/reinscrito,
// menos cancelado, menos pago (RPP + RPNP).
function saldoAPagar(r: RestoAPagar): number {
  return (
    Number(r.inscricao_processada) +
    Number(r.inscricao_nao_processada) +
    Number(r.reinscricao) -
    Number(r.cancelamento) -
    Number(r.rpp_pago) -
    Number(r.rpnp_pago)
  );
}

function agruparSomando(itens: RestoAPagar[], chaveDe: (r: RestoAPagar) => { chave: string; rotulo: string }): BarraDado[] {
  const mapa = new Map<string, BarraDado>();
  for (const r of itens) {
    const { chave, rotulo } = chaveDe(r);
    if (!mapa.has(chave)) mapa.set(chave, { chave, rotulo, valor: 0, cor: AZUL_SEQUENCIAL });
    mapa.get(chave)!.valor += saldoAPagar(r);
  }
  return Array.from(mapa.values()).sort((a, b) => b.valor - a.valor);
}

export function RestosAPagarGraficosPage() {
  const navigate = useNavigate();
  const { municipioSelecionadoId } = useScope();
  const [restos, setRestos] = useState<RestoAPagar[]>([]);
  const [mesesDisponiveis, setMesesDisponiveis] = useState<number[]>([]);
  const [mesSelecionado, setMesSelecionado] = useState<number | "">("");
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    setCarregando(true);
    buscarTodasPaginas<RestoAPagar>("/restos-a-pagar/", {})
      .then((todos) => {
        setRestos(todos);
        const meses = Array.from(new Set(todos.map((r) => r.mes_referencia))).sort((a, b) => a - b);
        setMesesDisponiveis(meses);
        setMesSelecionado((atual) => atual || meses[meses.length - 1] || "");
      })
      .finally(() => setCarregando(false));
  }, [municipioSelecionadoId]);

  const restosNoMes = useMemo(() => restos.filter((r) => r.mes_referencia === mesSelecionado), [restos, mesSelecionado]);

  const porExercicio = useMemo(
    () => agruparSomando(restosNoMes, (r) => ({ chave: String(r.exercicio_origem), rotulo: `Exercício ${r.exercicio_origem}` })),
    [restosNoMes]
  );

  const porUG = useMemo(
    () => agruparSomando(restosNoMes, (r) => ({ chave: String(r.unidade_gestora), rotulo: r.unidade_gestora_nome })),
    [restosNoMes]
  );

  // Evolução mensal: soma do saldo a pagar de TODAS as linhas de cada mês —
  // como cada arquivo RPxx.PDF já é um snapshot cumulativo (não um
  // movimento), este total já é "o saldo pendente visto naquele mês", sem
  // precisar somar meses entre si (ver docstring de RestoAPagar).
  const tendencia: PontoTendencia[] = useMemo(
    () =>
      mesesDisponiveis.map((m) => ({
        mes: m,
        valor: restos.filter((r) => r.mes_referencia === m).reduce((s, r) => s + saldoAPagar(r), 0),
      })),
    [restos, mesesDisponiveis]
  );

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/relatorios/restos-a-pagar")}>
          Voltar para a tabela
        </Button>
        <Typography variant="h5">Gráficos — Restos a Pagar</Typography>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <Typography variant="body2">Mês de referência:</Typography>
        <Select
          size="small"
          value={mesSelecionado}
          onChange={(e) => setMesSelecionado(Number(e.target.value))}
          displayEmpty
          sx={{ minWidth: 160 }}
        >
          {mesesDisponiveis.length === 0 && <MenuItem value="">Sem dados</MenuItem>}
          {mesesDisponiveis.map((m) => (
            <MenuItem key={m} value={m}>{MESES[m - 1]}</MenuItem>
          ))}
        </Select>
      </Box>

      {!carregando && restos.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography color="text.secondary">Nenhum resto a pagar importado.</Typography>
        </Paper>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <GraficoLinhaTendencia titulo="Evolução do Saldo a Pagar (todos os meses importados)" dados={tendencia} />
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <GraficoBarrasHorizontais
              titulo={`Saldo a Pagar por Exercício de Origem (${mesSelecionado ? MESES[Number(mesSelecionado) - 1] : "—"})`}
              dados={porExercicio}
            />
            <GraficoBarrasHorizontais
              titulo={`Saldo a Pagar por Unidade Gestora (${mesSelecionado ? MESES[Number(mesSelecionado) - 1] : "—"})`}
              dados={porUG}
            />
          </Box>
        </Box>
      )}
    </Box>
  );
}
