import { useEffect, useMemo, useState } from "react";
import { Box, Button, MenuItem, Paper, Select, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";
import { api, buscarTodasPaginas } from "../api/client";
import type { Exercicio, LancamentoExecucaoReceita, RestoAPagar, SaldoBalancoConta } from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { GraficoLinhaTendencia, type PontoTendencia } from "../components/charts/GraficoLinhaTendencia";

// D (Devedor) soma positivo, C (Credor) soma negativo — mesma convenção usada em SaldoBalancoPage/RelatorioFinanceiroPage.
function valorComSinal(valor: string, natureza: string): number {
  const n = Number(valor);
  return natureza === "C" ? -n : n;
}

export function RelatorioFinanceiroGraficosPage() {
  const navigate = useNavigate();
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [saldosAbertura, setSaldosAbertura] = useState<SaldoBalancoConta[]>([]);
  const [tendenciaCaixaBruta, setTendenciaCaixaBruta] = useState<PontoTendencia[]>([]);
  const [tendenciaLiquida, setTendenciaLiquida] = useState<PontoTendencia[]>([]);
  const [carregandoTendencia, setCarregandoTendencia] = useState(false);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        setExercicios(data.results);
        setExercicioId(data.results[0]?.id ?? "");
      });
    buscarTodasPaginas<SaldoBalancoConta>("/saldo-balanco/", {}).then((todas) => {
      const dataAbertura = todas.map((c) => c.data_referencia).sort()[0];
      setSaldosAbertura(todas.filter((c) => c.data_referencia === dataAbertura));
    });
  }, [municipioSelecionadoId]);

  const exercicioSelecionado = useMemo(
    () => exercicios.find((e) => e.id === exercicioId) ?? null,
    [exercicios, exercicioId]
  );
  const anoExercicio = exercicioSelecionado?.ano ?? new Date().getFullYear();

  // Mesma lógica de montarDisponibilidades()/derivar() de RelatorioFinanceiroPage.tsx,
  // só que calculando os TOTAIS do município (não por fonte) mês a mês — ver a nota
  // em CLAUDE.md sobre essa página para o detalhamento da fórmula.
  useEffect(() => {
    if (!exercicioSelecionado?.loa_id) {
      setTendenciaCaixaBruta([]);
      setTendenciaLiquida([]);
      return;
    }
    const loaId = exercicioSelecionado.loa_id;
    let cancelado = false;
    setCarregandoTendencia(true);
    Promise.all([
      api.get<{ mes_referencia: number; empenhado_acumulado: string; liquidado_acumulado: string; pago_acumulado: string }[]>(
        "/execucao-orcamentaria/tendencia/",
        { params: { loa: loaId } }
      ),
      buscarTodasPaginas<LancamentoExecucaoReceita>("/execucao-receita/", { loa: loaId }),
      buscarTodasPaginas<RestoAPagar>("/restos-a-pagar/", {}),
    ]).then(([{ data: tendenciaDespesa }, receitaTodos, restosTodos]) => {
      if (cancelado) return;

      const disponibilidadeCaixaBrutaAnterior = saldosAbertura.reduce(
        (acc, c) => acc + c.fontes.reduce((s, f) => s + valorComSinal(f.valor, f.natureza), 0),
        0
      );
      const saldoInicialRestos = restosTodos
        .filter((r) => r.mes_referencia === 1)
        .reduce((s, r) => s + Number(r.inscricao_processada) + Number(r.inscricao_nao_processada) + Number(r.reinscricao), 0);

      const caixaBruta: PontoTendencia[] = [];
      const liquida: PontoTendencia[] = [];
      for (const ponto of tendenciaDespesa) {
        const m = ponto.mes_referencia;
        const restosNoMes = restosTodos.filter((r) => r.mes_referencia === m);
        const cancelamentos = restosNoMes.reduce((s, r) => s + Number(r.cancelamento), 0);
        const pagamentosRestos = restosNoMes.reduce((s, r) => s + Number(r.rpp_pago) + Number(r.rpnp_pago), 0);
        const saldoRestosFinal = saldoInicialRestos - cancelamentos - pagamentosRestos;

        const receitas = receitaTodos
          .filter((l) => l.mes_referencia <= m)
          .reduce((s, l) => s + Number(l.valor_liquido_no_mes), 0);
        const pagamentosEmpenhos = Number(ponto.pago_acumulado);
        const inscricaoRPNP = Number(ponto.empenhado_acumulado) - Number(ponto.liquidado_acumulado);
        const inscricaoRP = Number(ponto.liquidado_acumulado) - Number(ponto.pago_acumulado);

        const ingressos = disponibilidadeCaixaBrutaAnterior + receitas;
        const dispendios = pagamentosRestos + pagamentosEmpenhos;
        const disponibilidadeCaixaBruta = ingressos - dispendios;
        const disponibilidadeLiquida = disponibilidadeCaixaBruta - (inscricaoRPNP + inscricaoRP) - saldoRestosFinal;

        caixaBruta.push({ mes: m, valor: disponibilidadeCaixaBruta });
        liquida.push({ mes: m, valor: disponibilidadeLiquida });
      }
      setTendenciaCaixaBruta(caixaBruta);
      setTendenciaLiquida(liquida);
    }).finally(() => {
      if (!cancelado) setCarregandoTendencia(false);
    });
    return () => {
      cancelado = true;
    };
  }, [exercicioSelecionado, saldosAbertura]);

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/relatorios/financeiro")}>
          Voltar para a tabela
        </Button>
        <Typography variant="h5">Gráficos — Apuração da Disponibilidade por Fonte</Typography>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
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
      </Box>

      {!exercicioSelecionado ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography color="text.secondary">Selecione um exercício para ver a evolução mensal.</Typography>
        </Paper>
      ) : carregandoTendencia ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography color="text.secondary">Carregando evolução mensal...</Typography>
        </Paper>
      ) : (
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <GraficoLinhaTendencia titulo={`Evolução da Disponibilidade de Caixa Bruta (${anoExercicio})`} dados={tendenciaCaixaBruta} />
          <GraficoLinhaTendencia titulo={`Evolução da Disponibilidade Líquida (${anoExercicio})`} dados={tendenciaLiquida} />
        </Box>
      )}
    </Box>
  );
}
