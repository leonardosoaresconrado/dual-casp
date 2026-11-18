import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Collapse,
  IconButton,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { api, buscarTodasPaginas } from "../api/client";
import type { Exercicio, LancamentoExecucaoReceita, RubricaReceita } from "../api/types";
import { useScope } from "../scope/ScopeContext";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

type Visualizacao = "acumulado" | "mes";

function formatarMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface GrupoReceita {
  codigo: string;
  nome: string;
  orcado: number;
  realizado: number;
  saldo: number;
  percentual: number;
  lancamentos: LancamentoExecucaoReceita[];
}

function agrupar(rubricas: RubricaReceita[], lancamentos: LancamentoExecucaoReceita[]): GrupoReceita[] {
  const mapa = new Map<string, GrupoReceita>();

  function grupo(codigo: string, nome: string): GrupoReceita {
    if (!mapa.has(codigo)) {
      mapa.set(codigo, { codigo, nome, orcado: 0, realizado: 0, saldo: 0, percentual: 0, lancamentos: [] });
    }
    return mapa.get(codigo)!;
  }

  for (const r of rubricas) {
    grupo(r.codigo, r.nome).orcado += Number(r.valor_orcado);
  }
  for (const l of lancamentos) {
    const r = l.rubrica_detalhe;
    const g = grupo(r.codigo, r.nome);
    g.realizado += Number(l.valor_liquido_no_mes);
    g.lancamentos.push(l);
  }
  for (const g of mapa.values()) {
    g.saldo = g.orcado - g.realizado;
    g.percentual = g.orcado !== 0 ? (g.realizado / g.orcado) * 100 : 0;
  }
  return Array.from(mapa.values()).sort((a, b) => b.orcado - a.orcado);
}

function LinhaGrupo({ grupo }: { grupo: GrupoReceita }) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox">
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell>
          {grupo.codigo} - {grupo.nome}
        </TableCell>
        <TableCell align="right">{formatarMoeda(grupo.orcado)}</TableCell>
        <TableCell align="right">{formatarMoeda(grupo.realizado)}</TableCell>
        <TableCell align="right">{formatarMoeda(grupo.saldo)}</TableCell>
        <TableCell sx={{ minWidth: 140 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <LinearProgress
              variant="determinate"
              value={Math.min(Math.max(grupo.percentual, 0), 100)}
              color={grupo.percentual >= 100 ? "success" : "primary"}
              sx={{ flex: 1, height: 8, borderRadius: 4 }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 40 }}>
              {grupo.percentual.toFixed(0)}%
            </Typography>
          </Box>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={6} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 2 }}>
              {grupo.lancamentos.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Nenhum lançamento de receita no período.
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Mês</TableCell>
                      <TableCell>Fonte de Recursos</TableCell>
                      <TableCell align="right">Valor Bruto</TableCell>
                      <TableCell align="right">Dedução</TableCell>
                      <TableCell align="right">Anulação</TableCell>
                      <TableCell align="right">Valor Líquido</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {grupo.lancamentos
                      .slice()
                      .sort(
                        (a, b) =>
                          a.mes_referencia - b.mes_referencia ||
                          a.rubrica_detalhe.fonte_recursos_nome.localeCompare(b.rubrica_detalhe.fonte_recursos_nome)
                      )
                      .map((l) => (
                        <TableRow key={l.id}>
                          <TableCell>{MESES[l.mes_referencia - 1]}</TableCell>
                          <TableCell>
                            {l.rubrica_detalhe.fonte_recursos_codigo} - {l.rubrica_detalhe.fonte_recursos_nome}
                          </TableCell>
                          <TableCell align="right">{formatarMoeda(Number(l.valor_bruto_no_mes))}</TableCell>
                          <TableCell align="right">{formatarMoeda(Number(l.deducao_no_mes))}</TableCell>
                          <TableCell align="right">{formatarMoeda(Number(l.anulacao_no_mes))}</TableCell>
                          <TableCell align="right">{formatarMoeda(Number(l.valor_liquido_no_mes))}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export function ReceitaPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  // 0 = ainda não sabemos qual é o último mês com movimento (definido
  // assim que os lançamentos do exercício chegam, abaixo) — nunca
  // mostrado no Select.
  const [mes, setMes] = useState<number>(0);
  const [visualizacao, setVisualizacao] = useState<Visualizacao>("acumulado");
  const [rubricas, setRubricas] = useState<RubricaReceita[]>([]);
  const [lancamentos, setLancamentos] = useState<LancamentoExecucaoReceita[]>([]);
  const [carregando, setCarregando] = useState(false);

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

  useEffect(() => {
    if (!exercicioSelecionado?.loa_id) {
      setRubricas([]);
      setLancamentos([]);
      return;
    }
    const loaId = exercicioSelecionado.loa_id;
    setCarregando(true);
    api
      .get<{ results: RubricaReceita[] }>("/rubricas-receita/", { params: { loa: loaId, page_size: 1000 } })
      .then(({ data }) => setRubricas(data.results));
    buscarTodasPaginas<LancamentoExecucaoReceita>("/execucao-receita/", { loa: loaId })
      .then((dados) => {
        setLancamentos(dados);
        // Seleciona automaticamente o último mês com movimento — nunca o
        // mês corrente do calendário, que pode não ter nenhum lançamento
        // ainda.
        if (dados.length > 0) {
          setMes(Math.max(...dados.map((d) => d.mes_referencia)));
        } else {
          setMes(new Date().getMonth() + 1);
        }
      })
      .finally(() => setCarregando(false));
  }, [exercicioSelecionado]);

  const lancamentosNoPeriodo = useMemo(
    () =>
      lancamentos.filter((l) =>
        visualizacao === "acumulado" ? l.mes_referencia <= mes : l.mes_referencia === mes
      ),
    [lancamentos, mes, visualizacao]
  );

  const grupos = useMemo(() => agrupar(rubricas, lancamentosNoPeriodo), [rubricas, lancamentosNoPeriodo]);

  const totais = useMemo(
    () =>
      grupos.reduce(
        (acc, g) => ({
          orcado: acc.orcado + g.orcado,
          realizado: acc.realizado + g.realizado,
        }),
        { orcado: 0, realizado: 0 }
      ),
    [grupos]
  );
  const percentualTotal = totais.orcado !== 0 ? (totais.realizado / totais.orcado) * 100 : 0;

  const rotuloPeriodo =
    visualizacao === "acumulado" ? `Acumulado até ${MESES[mes - 1]}` : `Movimento de ${MESES[mes - 1]}`;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Receita
      </Typography>

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

        <Select size="small" value={mes || ""} displayEmpty onChange={(e) => setMes(Number(e.target.value))} sx={{ minWidth: 160 }}>
          {!mes && <MenuItem value="">Carregando...</MenuItem>}
          {MESES.map((nome, idx) => (
            <MenuItem key={nome} value={idx + 1}>
              {nome}
            </MenuItem>
          ))}
        </Select>

        <ToggleButtonGroup
          size="small"
          exclusive
          value={visualizacao}
          onChange={(_e, novoValor: Visualizacao | null) => {
            if (novoValor) setVisualizacao(novoValor);
          }}
        >
          <ToggleButton value="acumulado">Acumulado até o mês</ToggleButton>
          <ToggleButton value="mes">Movimento do mês</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Previsto (LOA)
          </Typography>
          <Typography variant="h6">{formatarMoeda(totais.orcado)}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Realizado ({rotuloPeriodo})
          </Typography>
          <Typography variant="h6" color="success.main">
            {formatarMoeda(totais.realizado)}
          </Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Saldo a Realizar
          </Typography>
          <Typography variant="h6">{formatarMoeda(totais.orcado - totais.realizado)}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            % Realizado
          </Typography>
          <Typography variant="h6">{percentualTotal.toFixed(1)}%</Typography>
        </Paper>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>Código - Nome da Receita</TableCell>
              <TableCell align="right">Previsto</TableCell>
              <TableCell align="right">Realizado ({rotuloPeriodo})</TableCell>
              <TableCell align="right">Saldo</TableCell>
              <TableCell>% Realizado</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && grupos.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  Nenhuma receita para o período selecionado.
                </TableCell>
              </TableRow>
            )}
            {grupos.map((g) => (
              <LinhaGrupo key={g.codigo} grupo={g} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
