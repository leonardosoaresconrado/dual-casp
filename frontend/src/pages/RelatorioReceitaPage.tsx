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
import { api, buscarTodasPaginas } from "../api/client";
import type {
  ClassificacaoReceitaAlinea,
  ClassificacaoReceitaEspecie,
  ClassificacaoReceitaOrigem,
  ClassificacaoReceitaRubrica,
  ClassificacaoReceitaSubalinea,
  ClassificacaoReceitaTipo,
  Exercicio,
  LancamentoExecucaoReceita,
  RubricaReceita,
} from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { AZUL_SEQUENCIAL, formatarMoeda } from "../components/charts/GraficoLinhaTendencia";
import { GraficoBarrasHorizontais, type BarraDado } from "../components/charts/GraficoBarrasHorizontais";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

type Visualizacao = "acumulado" | "mes";
type Dimensao = "fonte" | "unidade_gestora" | "origem_stn" | "especie_stn" | "rubrica_stn";

const DIMENSOES: { valor: Dimensao; rotulo: string }[] = [
  { valor: "fonte", rotulo: "Fonte de Recursos" },
  { valor: "unidade_gestora", rotulo: "Unidade Gestora" },
  { valor: "origem_stn", rotulo: "Classificação STN — Origem" },
  { valor: "especie_stn", rotulo: "Classificação STN — Espécie" },
  { valor: "rubrica_stn", rotulo: "Classificação STN — Rubrica" },
];

// --- resolução da hierarquia oficial STN a partir de RubricaReceita.classificacao_tipo ---
// Cada RubricaReceita só guarda o FK do nível 7 (Tipo, folha); para agrupar por
// Origem/Espécie/Rubrica (níveis 2/3/4) é preciso subir a cadeia
// Tipo → Subalínea → Alínea → Rubrica(STN) → Espécie → Origem. Os 6 catálogos
// são pequenos (≤60 linhas cada, ver CLAUDE.md) — buscados uma vez, sem
// dependência de município/exercício (são catálogo nacional).

interface Catalogos {
  tipos: Map<number, ClassificacaoReceitaTipo>;
  subalineas: Map<number, ClassificacaoReceitaSubalinea>;
  alineas: Map<number, ClassificacaoReceitaAlinea>;
  rubricas: Map<number, ClassificacaoReceitaRubrica>;
  especies: Map<number, ClassificacaoReceitaEspecie>;
  origens: Map<number, ClassificacaoReceitaOrigem>;
}

interface NivelResolvido {
  chave: string;
  rotulo: string;
}

const SEM_CLASSIFICACAO: NivelResolvido = { chave: "__sem_classificacao__", rotulo: "(sem classificação STN)" };

function resolverCadeiaSTN(
  tipoId: number | null,
  cat: Catalogos
): { origem: NivelResolvido; especie: NivelResolvido; rubrica: NivelResolvido } {
  const tipo = tipoId != null ? cat.tipos.get(tipoId) : undefined;
  const subalinea = tipo ? cat.subalineas.get(tipo.subalinea) : undefined;
  const alinea = subalinea ? cat.alineas.get(subalinea.alinea) : undefined;
  const rubricaStn = alinea ? cat.rubricas.get(alinea.rubrica) : undefined;
  const especie = rubricaStn ? cat.especies.get(rubricaStn.especie) : undefined;
  const origem = especie ? cat.origens.get(especie.origem) : undefined;

  return {
    origem: origem
      ? { chave: String(origem.id), rotulo: `${origem.categoria_codigo}.${origem.codigo} - ${origem.nome}` }
      : SEM_CLASSIFICACAO,
    especie: especie
      ? { chave: String(especie.id), rotulo: `${especie.origem_codigo}.${especie.codigo} - ${especie.nome}` }
      : SEM_CLASSIFICACAO,
    rubrica: rubricaStn
      ? { chave: String(rubricaStn.id), rotulo: `${rubricaStn.especie_codigo}.${rubricaStn.codigo} - ${rubricaStn.nome}` }
      : SEM_CLASSIFICACAO,
  };
}

function chaveEDimensao(r: RubricaReceita, dimensao: Dimensao, cat: Catalogos): NivelResolvido {
  switch (dimensao) {
    case "fonte":
      return { chave: String(r.fonte_recursos), rotulo: `${r.fonte_recursos_codigo} - ${r.fonte_recursos_nome}` };
    case "unidade_gestora":
      return { chave: String(r.unidade_gestora), rotulo: r.unidade_gestora_nome };
    case "origem_stn":
      return resolverCadeiaSTN(r.classificacao_tipo, cat).origem;
    case "especie_stn":
      return resolverCadeiaSTN(r.classificacao_tipo, cat).especie;
    case "rubrica_stn":
      return resolverCadeiaSTN(r.classificacao_tipo, cat).rubrica;
  }
}

// --- agrupamento --------------------------------------------------------------

interface LinhaRubrica {
  id: number;
  codigo: string;
  nome: string;
  fonte: string;
  orcado: number;
  realizado: number;
  saldo: number;
  percentual: number;
}

interface Grupo {
  chave: string;
  rotulo: string;
  orcado: number;
  realizado: number;
  saldo: number;
  percentual: number;
  linhas: LinhaRubrica[];
}

function agrupar(
  rubricas: RubricaReceita[],
  lancamentosNoPeriodo: LancamentoExecucaoReceita[],
  dimensao: Dimensao,
  cat: Catalogos
): Grupo[] {
  const realizadoPorRubrica = new Map<number, number>();
  for (const l of lancamentosNoPeriodo) {
    realizadoPorRubrica.set(l.rubrica, (realizadoPorRubrica.get(l.rubrica) ?? 0) + Number(l.valor_liquido_no_mes));
  }

  const mapa = new Map<string, Grupo>();
  for (const r of rubricas) {
    const { chave, rotulo } = chaveEDimensao(r, dimensao, cat);
    if (!mapa.has(chave)) {
      mapa.set(chave, { chave, rotulo, orcado: 0, realizado: 0, saldo: 0, percentual: 0, linhas: [] });
    }
    const g = mapa.get(chave)!;
    const orcado = Number(r.valor_orcado);
    const realizado = realizadoPorRubrica.get(r.id) ?? 0;
    g.orcado += orcado;
    g.realizado += realizado;
    g.linhas.push({
      id: r.id,
      codigo: r.codigo,
      nome: r.nome,
      fonte: `${r.fonte_recursos_codigo} - ${r.fonte_recursos_nome}`,
      orcado,
      realizado,
      saldo: orcado - realizado,
      percentual: orcado !== 0 ? (realizado / orcado) * 100 : 0,
    });
  }
  for (const g of mapa.values()) {
    g.saldo = g.orcado - g.realizado;
    g.percentual = g.orcado !== 0 ? (g.realizado / g.orcado) * 100 : 0;
    g.linhas.sort((a, b) => b.orcado - a.orcado);
  }
  return Array.from(mapa.values()).sort((a, b) => b.realizado - a.realizado);
}

// --- tabela de agrupamento (pivot expansível) --------------------------------

function LinhaGrupo({ grupo, rotuloPeriodo }: { grupo: Grupo; rotuloPeriodo: string }) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer", bgcolor: "action.hover" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox">
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell sx={{ fontWeight: "bold" }}>{grupo.rotulo}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.orcado)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.realizado)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.saldo)}</TableCell>
        <TableCell sx={{ fontWeight: "bold" }}>{grupo.percentual.toFixed(1)}%</TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={6} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 1 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Código - Nome da Receita</TableCell>
                    <TableCell>Fonte de Recursos</TableCell>
                    <TableCell align="right">Previsto</TableCell>
                    <TableCell align="right">Realizado ({rotuloPeriodo})</TableCell>
                    <TableCell align="right">Saldo</TableCell>
                    <TableCell>% Realizado</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.linhas.map((l) => (
                    <TableRow key={l.id}>
                      <TableCell>{l.codigo} - {l.nome}</TableCell>
                      <TableCell>{l.fonte}</TableCell>
                      <TableCell align="right">{formatarMoeda(l.orcado)}</TableCell>
                      <TableCell align="right">{formatarMoeda(l.realizado)}</TableCell>
                      <TableCell align="right">{formatarMoeda(l.saldo)}</TableCell>
                      <TableCell>{l.percentual.toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
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

export function RelatorioReceitaPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  // 0 = ainda não sabemos qual é o último mês com movimento (definido
  // assim que os lançamentos do exercício chegam, abaixo) — nunca
  // mostrado no Select.
  const [mes, setMes] = useState<number>(0);
  const [visualizacao, setVisualizacao] = useState<Visualizacao>("acumulado");
  const [dimensao, setDimensao] = useState<Dimensao>("fonte");
  const [filtroDimensao, setFiltroDimensao] = useState<Dimensao | "">("");
  const [filtroValor, setFiltroValor] = useState<string>("");
  const [rubricas, setRubricas] = useState<RubricaReceita[]>([]);
  const [lancamentos, setLancamentos] = useState<LancamentoExecucaoReceita[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        setExercicios(data.results);
        setExercicioId(data.results[0]?.id ?? "");
      });
  }, [municipioSelecionadoId]);

  // Catálogo oficial STN — independente de município/exercício, buscado uma
  // única vez (6 listas pequenas, ≤60 linhas cada).
  useEffect(() => {
    Promise.all([
      api.get<{ results: ClassificacaoReceitaTipo[] }>("/classificacao-receita-tipos/", { params: { page_size: 200 } }),
      api.get<{ results: ClassificacaoReceitaSubalinea[] }>("/classificacao-receita-subalineas/", { params: { page_size: 200 } }),
      api.get<{ results: ClassificacaoReceitaAlinea[] }>("/classificacao-receita-alineas/", { params: { page_size: 200 } }),
      api.get<{ results: ClassificacaoReceitaRubrica[] }>("/classificacao-receita-rubricas/", { params: { page_size: 200 } }),
      api.get<{ results: ClassificacaoReceitaEspecie[] }>("/classificacao-receita-especies/", { params: { page_size: 200 } }),
      api.get<{ results: ClassificacaoReceitaOrigem[] }>("/classificacao-receita-origens/", { params: { page_size: 200 } }),
    ]).then(([tipos, subalineas, alineas, rubricasStn, especies, origens]) => {
      setCatalogos({
        tipos: new Map(tipos.data.results.map((t) => [t.id, t])),
        subalineas: new Map(subalineas.data.results.map((s) => [s.id, s])),
        alineas: new Map(alineas.data.results.map((a) => [a.id, a])),
        rubricas: new Map(rubricasStn.data.results.map((r) => [r.id, r])),
        especies: new Map(especies.data.results.map((e) => [e.id, e])),
        origens: new Map(origens.data.results.map((o) => [o.id, o])),
      });
    });
  }, []);

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

  // Opções do "Filtrar por" = valores distintos da dimensão escolhida,
  // tirados das rubricas já carregadas (client-side, mesmo padrão do
  // "Agrupar por").
  const opcoesFiltro = useMemo(() => {
    if (!filtroDimensao || !catalogos) return [];
    const mapa = new Map<string, string>();
    for (const r of rubricas) {
      const { chave, rotulo } = chaveEDimensao(r, filtroDimensao, catalogos);
      if (!mapa.has(chave)) mapa.set(chave, rotulo);
    }
    return Array.from(mapa, ([chave, rotulo]) => ({ chave, rotulo })).sort((a, b) => a.rotulo.localeCompare(b.rotulo));
  }, [rubricas, filtroDimensao, catalogos]);

  const rubricasFiltradas = useMemo(() => {
    if (!filtroDimensao || !filtroValor || !catalogos) return rubricas;
    return rubricas.filter((r) => chaveEDimensao(r, filtroDimensao, catalogos).chave === filtroValor);
  }, [rubricas, filtroDimensao, filtroValor, catalogos]);

  const grupos = useMemo(
    () => (catalogos ? agrupar(rubricasFiltradas, lancamentosNoPeriodo, dimensao, catalogos) : []),
    [rubricasFiltradas, lancamentosNoPeriodo, dimensao, catalogos]
  );

  const totais = useMemo(
    () =>
      grupos.reduce(
        (acc, g) => ({ orcado: acc.orcado + g.orcado, realizado: acc.realizado + g.realizado }),
        { orcado: 0, realizado: 0 }
      ),
    [grupos]
  );
  const percentualTotal = totais.orcado !== 0 ? (totais.realizado / totais.orcado) * 100 : 0;

  const barrasPrevisto: BarraDado[] = useMemo(() => {
    const top = grupos.slice().sort((a, b) => b.orcado - a.orcado).slice(0, 7);
    const resto = grupos.slice(7).reduce((soma, g) => soma + g.orcado, 0);
    const base: BarraDado[] = top.map((g) => ({ chave: g.chave, rotulo: g.rotulo, valor: g.orcado, cor: AZUL_SEQUENCIAL }));
    if (resto > 0) base.push({ chave: "__outros__", rotulo: "Outros", valor: resto, cor: AZUL_SEQUENCIAL });
    return base;
  }, [grupos]);

  const barrasRealizado: BarraDado[] = useMemo(() => {
    const top = grupos.slice(0, 7);
    const resto = grupos.slice(7).reduce((soma, g) => soma + g.realizado, 0);
    const base: BarraDado[] = top.map((g) => ({ chave: g.chave, rotulo: g.rotulo, valor: g.realizado, cor: AZUL_SEQUENCIAL }));
    if (resto > 0) base.push({ chave: "__outros__", rotulo: "Outros", valor: resto, cor: AZUL_SEQUENCIAL });
    return base;
  }, [grupos]);

  const rotuloPeriodo =
    visualizacao === "acumulado" ? `Acumulado até ${MESES[mes - 1]}` : `Movimento de ${MESES[mes - 1]}`;
  const rotuloDimensao = DIMENSOES.find((d) => d.valor === dimensao)?.rotulo ?? "";

  function exportarCSV() {
    const linhas = [
      [rotuloDimensao, "Previsto", "Realizado", "Saldo", "% Realizado"],
      ...grupos.map((g) => [
        g.rotulo,
        g.orcado.toFixed(2).replace(".", ","),
        g.realizado.toFixed(2).replace(".", ","),
        g.saldo.toFixed(2).replace(".", ","),
        g.percentual.toFixed(1).replace(".", ","),
      ]),
    ];
    const csv = linhas.map((linha) => linha.map((c) => `"${c}"`).join(";")).join("\r\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio-receita-${rotuloDimensao.toLowerCase().replace(/\s+/g, "-")}-${MESES[mes - 1].toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Relatório Dinâmico da Receita
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

        <Select size="small" value={dimensao} onChange={(e) => setDimensao(e.target.value as Dimensao)} sx={{ minWidth: 240 }}>
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
          sx={{ minWidth: 240 }}
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
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">Previsto (LOA)</Typography>
          <Typography variant="h6">{formatarMoeda(totais.orcado)}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">Realizado ({rotuloPeriodo})</Typography>
          <Typography variant="h6" color="success.main">{formatarMoeda(totais.realizado)}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">Saldo a Realizar</Typography>
          <Typography variant="h6">{formatarMoeda(totais.orcado - totais.realizado)}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">% Realizado</Typography>
          <Typography variant="h6">{percentualTotal.toFixed(1)}%</Typography>
        </Paper>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <GraficoBarrasHorizontais titulo={`Previsto por ${rotuloDimensao}`} dados={barrasPrevisto} />
        <GraficoBarrasHorizontais titulo={`Realizado por ${rotuloDimensao} (${rotuloPeriodo})`} dados={barrasRealizado} />
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>{rotuloDimensao}</TableCell>
              <TableCell align="right">Previsto</TableCell>
              <TableCell align="right">Realizado ({rotuloPeriodo})</TableCell>
              <TableCell align="right">Saldo</TableCell>
              <TableCell>% Realizado</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && grupos.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">Nenhuma receita para o período selecionado.</TableCell>
              </TableRow>
            )}
            {grupos.map((g) => (
              <LinhaGrupo key={g.chave} grupo={g} rotuloPeriodo={rotuloPeriodo} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
