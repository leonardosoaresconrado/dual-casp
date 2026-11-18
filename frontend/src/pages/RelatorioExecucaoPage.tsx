import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Collapse,
  IconButton,
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
import DownloadIcon from "@mui/icons-material/Download";
import PrintIcon from "@mui/icons-material/Print";
import { api, buscarTodasPaginas, buscarUltimoMesComMovimento } from "../api/client";
import type { Exercicio, LancamentoExecucaoOrcamentaria, OrigemDotacao, UnidadeGestora } from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { AZUL_SEQUENCIAL, formatarMoeda } from "../components/charts/GraficoLinhaTendencia";
import { GraficoBarrasHorizontais, type BarraDado } from "../components/charts/GraficoBarrasHorizontais";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

// paleta validada (dataviz skill) — node scripts/validate_palette.js
// "#2a78d6,#eb6834,#1baf7a,#eda100" --mode light => PASS (contraste WARN em
// aqua/amarelo mitigado por rótulo direto, já aplicado abaixo)
const ORIGEM_COR: Record<OrigemDotacao, string> = {
  ORCAMENTO: "#2a78d6",
  CREDITO_SUPLEMENTAR: "#eb6834",
  CREDITO_ESPECIAL: "#1baf7a",
  CREDITO_ADICIONAL: "#eda100",
};
const ORIGEM_LABEL: Record<OrigemDotacao, string> = {
  ORCAMENTO: "Orçamento",
  CREDITO_SUPLEMENTAR: "Créd. Suplementar",
  CREDITO_ESPECIAL: "Créd. Especial",
  CREDITO_ADICIONAL: "Créd. Adicional",
};
const ORDEM_ORIGEM: OrigemDotacao[] = ["ORCAMENTO", "CREDITO_SUPLEMENTAR", "CREDITO_ESPECIAL", "CREDITO_ADICIONAL"];

type Visualizacao = "acumulado" | "mes";
type Dimensao = "unidade_gestora" | "orgao" | "funcao" | "subfuncao" | "programa" | "origem" | "fonte";

const DIMENSOES: { valor: Dimensao; rotulo: string }[] = [
  { valor: "unidade_gestora", rotulo: "Unidade Gestora" },
  { valor: "orgao", rotulo: "Órgão" },
  { valor: "funcao", rotulo: "Função" },
  { valor: "subfuncao", rotulo: "Subfunção" },
  { valor: "programa", rotulo: "Programa" },
  { valor: "origem", rotulo: "Origem da Dotação" },
  { valor: "fonte", rotulo: "Fonte de Recursos" },
];

function chaveEDimensao(l: LancamentoExecucaoOrcamentaria, dimensao: Dimensao): { chave: string; rotulo: string } {
  const r = l.rubrica_detalhe;
  switch (dimensao) {
    case "unidade_gestora":
      return { chave: String(r.unidade_gestora), rotulo: r.unidade_gestora_nome };
    case "orgao":
      return { chave: r.orgao_codigo, rotulo: `${r.orgao_codigo} - ${r.orgao_nome}` };
    case "funcao":
      return { chave: r.funcao_codigo, rotulo: `${r.funcao_codigo} - ${r.funcao_nome}` };
    case "subfuncao":
      return { chave: `${r.funcao_codigo}.${r.subfuncao_codigo}`, rotulo: `${r.subfuncao_codigo} - ${r.subfuncao_nome}` };
    case "programa":
      return { chave: r.programa_codigo, rotulo: `${r.programa_codigo} - ${r.programa_nome}` };
    case "origem":
      return { chave: r.origem_dotacao, rotulo: r.origem_dotacao_label };
    case "fonte":
      return { chave: r.fonte_recursos_codigo, rotulo: `${r.fonte_recursos_codigo} - ${r.fonte_recursos_nome}` };
  }
}

interface Grupo {
  chave: string;
  rotulo: string;
  dotacao: number;
  empenhado: number;
  liquidado: number;
  pago: number;
  saldo: number;
  itens: LancamentoExecucaoOrcamentaria[];
}

function valorPeriodo(l: LancamentoExecucaoOrcamentaria, visualizacao: Visualizacao) {
  return {
    empenhado: Number(visualizacao === "acumulado" ? l.empenhado_acumulado : l.empenhado_no_mes),
    liquidado: Number(visualizacao === "acumulado" ? l.liquidado_acumulado : l.liquidado_no_mes),
    pago: Number(visualizacao === "acumulado" ? l.pago_acumulado : l.pago_no_mes),
  };
}

function agrupar(lancamentos: LancamentoExecucaoOrcamentaria[], dimensao: Dimensao, visualizacao: Visualizacao): Grupo[] {
  const mapa = new Map<string, Grupo>();
  for (const l of lancamentos) {
    const { chave, rotulo } = chaveEDimensao(l, dimensao);
    const vp = valorPeriodo(l, visualizacao);
    if (!mapa.has(chave)) {
      mapa.set(chave, { chave, rotulo, dotacao: 0, empenhado: 0, liquidado: 0, pago: 0, saldo: 0, itens: [] });
    }
    const g = mapa.get(chave)!;
    g.dotacao += Number(l.dotacao_atualizada);
    g.empenhado += vp.empenhado;
    g.liquidado += vp.liquidado;
    g.pago += vp.pago;
    g.saldo += Number(l.saldo_a_empenhar);
    g.itens.push(l);
  }
  return Array.from(mapa.values()).sort((a, b) => b.empenhado - a.empenhado);
}

// --- tabela de agrupamento (pivot expansível) --------------------------------

function LinhaGrupo({ grupo, visualizacao }: { grupo: Grupo; visualizacao: Visualizacao }) {
  const [aberto, setAberto] = useState(false);
  const rotuloPeriodo = visualizacao === "acumulado" ? "acum." : "mês";

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer", bgcolor: "action.hover" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox">
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell sx={{ fontWeight: "bold" }}>{grupo.rotulo}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.dotacao)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.empenhado)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.liquidado)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.pago)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.saldo)}</TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={7} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 1 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Órgão / Unidade</TableCell>
                    <TableCell>Ação</TableCell>
                    <TableCell align="right">Dotação Atualizada</TableCell>
                    <TableCell align="right">Empenhado ({rotuloPeriodo})</TableCell>
                    <TableCell align="right">Liquidado ({rotuloPeriodo})</TableCell>
                    <TableCell align="right">Pago ({rotuloPeriodo})</TableCell>
                    <TableCell align="right">Saldo a Empenhar</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.itens.map((l) => {
                    const vp = valorPeriodo(l, visualizacao);
                    const r = l.rubrica_detalhe;
                    return (
                      <TableRow key={l.id}>
                        <TableCell>{r.orgao_nome} / {r.unidade_orcamentaria_nome}</TableCell>
                        <TableCell>{r.acao_codigo} - {r.acao_nome}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(l.dotacao_atualizada))}</TableCell>
                        <TableCell align="right">{formatarMoeda(vp.empenhado)}</TableCell>
                        <TableCell align="right">{formatarMoeda(vp.liquidado)}</TableCell>
                        <TableCell align="right">{formatarMoeda(vp.pago)}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(l.saldo_a_empenhar))}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

// --- página principal ---------------------------------------------------------

export function RelatorioExecucaoPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  // 0 = ainda não sabemos qual é o último mês com movimento (ver efeito
  // abaixo) — nunca mostrado no Select, só evita buscar com o mês errado.
  const [mes, setMes] = useState<number>(0);
  const [unidadesGestoras, setUnidadesGestoras] = useState<UnidadeGestora[]>([]);
  const [ugId, setUgId] = useState<number | "">("");
  const [visualizacao, setVisualizacao] = useState<Visualizacao>("acumulado");
  const [dimensao, setDimensao] = useState<Dimensao>("unidade_gestora");
  const [filtroDimensao, setFiltroDimensao] = useState<Dimensao | "">("");
  const [filtroValor, setFiltroValor] = useState<string>("");
  const [lancamentos, setLancamentos] = useState<LancamentoExecucaoOrcamentaria[]>([]);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        setExercicios(data.results);
        setExercicioId(data.results[0]?.id ?? "");
      });
    api
      .get<{ results: UnidadeGestora[] }>("/unidades-gestoras/", {
        params: { municipio: municipioSelecionadoId, page_size: 50 },
      })
      .then(({ data }) => setUnidadesGestoras(data.results));
  }, [municipioSelecionadoId]);

  const exercicioSelecionado = useMemo(
    () => exercicios.find((e) => e.id === exercicioId) ?? null,
    [exercicios, exercicioId]
  );

  // Seleciona automaticamente o último mês com empenho ao trocar de
  // exercício — nunca o mês corrente do calendário.
  useEffect(() => {
    if (!exercicioSelecionado?.loa_id) return;
    let cancelado = false;
    buscarUltimoMesComMovimento(exercicioSelecionado.loa_id).then((ultimoMes) => {
      if (cancelado) return;
      setMes(ultimoMes ?? new Date().getMonth() + 1);
    });
    return () => {
      cancelado = true;
    };
  }, [exercicioSelecionado]);

  useEffect(() => {
    if (!exercicioSelecionado?.loa_id || !mes) {
      setLancamentos([]);
      return;
    }
    setCarregando(true);
    buscarTodasPaginas<LancamentoExecucaoOrcamentaria>("/execucao-orcamentaria/", {
      loa: exercicioSelecionado.loa_id,
      mes_referencia: mes,
      unidade_gestora: ugId || undefined,
    })
      .then(setLancamentos)
      .finally(() => setCarregando(false));
  }, [exercicioSelecionado, mes, ugId]);

  // Opções do "Filtrar por" = valores distintos da dimensão escolhida,
  // tirados dos lançamentos já carregados (client-side, mesmo padrão do
  // "Agrupar por" — nenhuma chamada nova ao backend).
  const opcoesFiltro = useMemo(() => {
    if (!filtroDimensao) return [];
    const mapa = new Map<string, string>();
    for (const l of lancamentos) {
      const { chave, rotulo } = chaveEDimensao(l, filtroDimensao);
      if (!mapa.has(chave)) mapa.set(chave, rotulo);
    }
    return Array.from(mapa, ([chave, rotulo]) => ({ chave, rotulo })).sort((a, b) => a.rotulo.localeCompare(b.rotulo));
  }, [lancamentos, filtroDimensao]);

  const lancamentosFiltrados = useMemo(() => {
    if (!filtroDimensao || !filtroValor) return lancamentos;
    return lancamentos.filter((l) => chaveEDimensao(l, filtroDimensao).chave === filtroValor);
  }, [lancamentos, filtroDimensao, filtroValor]);

  const grupos = useMemo(
    () => agrupar(lancamentosFiltrados, dimensao, visualizacao),
    [lancamentosFiltrados, dimensao, visualizacao]
  );

  const totais = useMemo(
    () =>
      lancamentosFiltrados.reduce(
        (acc, l) => {
          const vp = valorPeriodo(l, visualizacao);
          return {
            dotacao: acc.dotacao + Number(l.dotacao_atualizada),
            empenhado: acc.empenhado + vp.empenhado,
            liquidado: acc.liquidado + vp.liquidado,
            pago: acc.pago + vp.pago,
          };
        },
        { dotacao: 0, empenhado: 0, liquidado: 0, pago: 0 }
      ),
    [lancamentosFiltrados, visualizacao]
  );

  // gráfico de magnitude: top 7 grupos pelo critério escolhido + "Outros"
  const barrasMagnitude: BarraDado[] = useMemo(() => {
    const top = grupos.slice(0, 7);
    const resto = grupos.slice(7).reduce((soma, g) => soma + g.empenhado, 0);
    const base: BarraDado[] = top.map((g) => ({ chave: g.chave, rotulo: g.rotulo, valor: g.empenhado, cor: AZUL_SEQUENCIAL }));
    if (resto > 0) base.push({ chave: "__outros__", rotulo: "Outros", valor: resto, cor: AZUL_SEQUENCIAL });
    return base;
  }, [grupos]);

  const barrasOrigem: BarraDado[] = useMemo(() => {
    const porOrigem = new Map<OrigemDotacao, number>();
    for (const l of lancamentosFiltrados) {
      const o = l.rubrica_detalhe.origem_dotacao;
      porOrigem.set(o, (porOrigem.get(o) ?? 0) + Number(l.dotacao_atualizada));
    }
    return ORDEM_ORIGEM.filter((o) => (porOrigem.get(o) ?? 0) > 0).map((o) => ({
      chave: o,
      rotulo: ORIGEM_LABEL[o],
      valor: porOrigem.get(o) ?? 0,
      cor: ORIGEM_COR[o],
    }));
  }, [lancamentosFiltrados]);

  const rotuloPeriodo =
    visualizacao === "acumulado" ? `Acumulado até ${MESES[mes - 1]}` : `Movimento de ${MESES[mes - 1]}`;
  const rotuloDimensao = DIMENSOES.find((d) => d.valor === dimensao)?.rotulo ?? "";

  function exportarCSV() {
    const linhas = [
      [rotuloDimensao, "Dotação Atualizada", "Empenhado", "Liquidado", "Pago", "Saldo a Empenhar"],
      ...grupos.map((g) => [
        g.rotulo,
        g.dotacao.toFixed(2).replace(".", ","),
        g.empenhado.toFixed(2).replace(".", ","),
        g.liquidado.toFixed(2).replace(".", ","),
        g.pago.toFixed(2).replace(".", ","),
        g.saldo.toFixed(2).replace(".", ","),
      ]),
    ];
    const csv = linhas.map((linha) => linha.map((c) => `"${c}"`).join(";")).join("\r\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `execucao-orcamentaria-${rotuloDimensao.toLowerCase().replace(/\s+/g, "-")}-${MESES[mes - 1].toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Relatório Dinâmico da Execução Orçamentária
      </Typography>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <Select size="small" value={exercicioId} onChange={(e) => setExercicioId(Number(e.target.value))} displayEmpty sx={{ minWidth: 160 }}>
          {exercicios.length === 0 && <MenuItem value="">Sem exercícios</MenuItem>}
          {exercicios.map((ex) => (
            <MenuItem key={ex.id} value={ex.id}>Exercício {ex.ano}</MenuItem>
          ))}
        </Select>

        <Select size="small" value={mes || ""} displayEmpty onChange={(e) => setMes(Number(e.target.value))} sx={{ minWidth: 160 }}>
          {!mes && <MenuItem value="">Carregando...</MenuItem>}
          {MESES.map((nome, idx) => (
            <MenuItem key={nome} value={idx + 1}>{nome}</MenuItem>
          ))}
        </Select>

        <Select
          size="small"
          value={ugId}
          displayEmpty
          onChange={(e) => {
            const valor = e.target.value as number | "";
            setUgId(valor === "" ? "" : Number(valor));
          }}
          sx={{ minWidth: 260 }}
        >
          <MenuItem value="">Todas as Unidades Gestoras</MenuItem>
          {unidadesGestoras.map((ug) => (
            <MenuItem key={ug.id} value={ug.id}>{ug.nome}</MenuItem>
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

        <Select size="small" value={dimensao} onChange={(e) => setDimensao(e.target.value as Dimensao)} sx={{ minWidth: 200 }}>
          {DIMENSOES.map((d) => (
            <MenuItem key={d.valor} value={d.valor}>Agrupar por {d.rotulo}</MenuItem>
          ))}
        </Select>

        <Select
          size="small"
          value={filtroDimensao}
          displayEmpty
          onChange={(e) => {
            setFiltroDimensao(e.target.value as Dimensao | "");
            setFiltroValor("");
          }}
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">Sem filtro</MenuItem>
          {DIMENSOES.map((d) => (
            <MenuItem key={d.valor} value={d.valor}>Filtrar por {d.rotulo}</MenuItem>
          ))}
        </Select>

        {filtroDimensao && (
          <Select
            size="small"
            value={filtroValor}
            displayEmpty
            onChange={(e) => setFiltroValor(e.target.value)}
            sx={{ minWidth: 220 }}
          >
            <MenuItem value="">Todos</MenuItem>
            {opcoesFiltro.map((o) => (
              <MenuItem key={o.chave} value={o.chave}>{o.rotulo}</MenuItem>
            ))}
          </Select>
        )}

        <Box sx={{ flexGrow: 1 }} />

        <Button size="small" startIcon={<DownloadIcon />} onClick={exportarCSV} variant="outlined">
          Exportar CSV
        </Button>
        <Button size="small" startIcon={<PrintIcon />} onClick={() => window.print()} variant="outlined">
          Imprimir
        </Button>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        {([
          ["Dotação Atualizada", totais.dotacao, undefined],
          [`Empenhado (${rotuloPeriodo})`, totais.empenhado, "warning.main"],
          [`Liquidado (${rotuloPeriodo})`, totais.liquidado, "info.main"],
          [`Pago (${rotuloPeriodo})`, totais.pago, "success.main"],
        ] as const).map(([titulo, valor, cor]) => (
          <Paper key={titulo} variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
            <Typography variant="body2" color="text.secondary">{titulo}</Typography>
            <Typography variant="h6" sx={{ color: cor }}>{formatarMoeda(valor)}</Typography>
          </Paper>
        ))}
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <GraficoBarrasHorizontais
          titulo={`Empenhado por ${rotuloDimensao} (${rotuloPeriodo})`}
          dados={barrasMagnitude}
        />
        <GraficoBarrasHorizontais
          titulo="Dotação Atualizada por Origem"
          dados={barrasOrigem}
          comSwatch
        />
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>{rotuloDimensao}</TableCell>
              <TableCell align="right">Dotação Atualizada</TableCell>
              <TableCell align="right">Empenhado ({rotuloPeriodo})</TableCell>
              <TableCell align="right">Liquidado ({rotuloPeriodo})</TableCell>
              <TableCell align="right">Pago ({rotuloPeriodo})</TableCell>
              <TableCell align="right">Saldo a Empenhar</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && grupos.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">Nenhum lançamento para o período selecionado.</TableCell>
              </TableRow>
            )}
            {grupos.map((g) => (
              <LinhaGrupo key={g.chave} grupo={g} visualizacao={visualizacao} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
