import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { api, buscarTodasPaginas, buscarUltimoMesComMovimento } from "../api/client";
import type {
  Empenho,
  Exercicio,
  LancamentoExecucaoOrcamentaria,
  OrigemDotacao,
  UnidadeGestora,
} from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { AcoesRegistroManual, type CampoEdicao } from "../components/AcoesRegistroManual";

const CAMPOS_EDICAO_EMPENHO: CampoEdicao[] = [
  { chave: "numero", rotulo: "Número do Empenho", tipo: "texto" },
  { chave: "data_empenho", rotulo: "Data do Empenho", tipo: "data" },
  { chave: "credor", rotulo: "Credor", tipo: "texto" },
  { chave: "historico", rotulo: "Histórico", tipo: "texto" },
];

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

const ORIGEM_COR: Record<OrigemDotacao, "success" | "info" | "warning" | "default"> = {
  ORCAMENTO: "success",
  CREDITO_SUPLEMENTAR: "info",
  CREDITO_ESPECIAL: "warning",
  CREDITO_ADICIONAL: "default",
};

type Visualizacao = "acumulado" | "mes";

function formatarMoeda(valor: string | number): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarData(data: string): string {
  return new Date(`${data}T00:00:00`).toLocaleDateString("pt-BR");
}

function CardResumo({ titulo, valor, cor }: { titulo: string; valor: number; cor?: string }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, minWidth: 180, flex: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {titulo}
      </Typography>
      <Typography variant="h6" sx={{ color: cor }}>
        {formatarMoeda(valor)}
      </Typography>
    </Paper>
  );
}

function valoresDoEmpenhoNoPeriodo(empenho: Empenho, mes: number, visualizacao: Visualizacao) {
  if (visualizacao === "mes") {
    const doMes = empenho.movimentos.find((m) => m.mes_referencia === mes);
    return {
      empenhado: Number(doMes?.valor_empenho_no_mes ?? 0),
      liquidado: Number(doMes?.valor_liquidado_no_mes ?? 0),
      pago: Number(doMes?.valor_pago_no_mes ?? 0),
    };
  }
  return empenho.movimentos
    .filter((m) => m.mes_referencia <= mes)
    .reduce(
      (acc, m) => ({
        empenhado: acc.empenhado + Number(m.valor_empenho_no_mes),
        liquidado: acc.liquidado + Number(m.valor_liquidado_no_mes),
        pago: acc.pago + Number(m.valor_pago_no_mes),
      }),
      { empenhado: 0, liquidado: 0, pago: 0 }
    );
}

// Em "acumulado", um empenho só é relevante se já tinha alguma movimentação até o
// mês selecionado (senão ainda "não existia" nesse ponto do tempo); em "mês", só
// é relevante se teve movimentação exatamente naquele mês. Em ambos os casos,
// movimentos de meses posteriores ao selecionado nunca devem aparecer — ver
// histórico de conversa: um empenho de setembro aparecia ao filtrar por janeiro.
function empenhoRelevanteNoPeriodo(empenho: Empenho, mes: number, visualizacao: Visualizacao): boolean {
  return empenho.movimentos.some((m) =>
    visualizacao === "acumulado" ? m.mes_referencia <= mes : m.mes_referencia === mes
  );
}

function LinhaEmpenhos({
  empenhos,
  carregando,
  mes,
  visualizacao,
  onAlterado,
}: {
  empenhos: Empenho[] | null;
  carregando: boolean;
  mes: number;
  visualizacao: Visualizacao;
  onAlterado: () => void;
}) {
  if (carregando) {
    return (
      <Typography variant="body2" color="text.secondary">
        Carregando empenhos...
      </Typography>
    );
  }
  if (!empenhos || empenhos.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Nenhum empenho registrado para esta rubrica.
      </Typography>
    );
  }
  const empenhosNoPeriodo = empenhos.filter((e) => empenhoRelevanteNoPeriodo(e, mes, visualizacao));
  if (empenhosNoPeriodo.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Nenhum empenho com movimentação em {MESES[mes - 1]} ou antes.
      </Typography>
    );
  }
  const rotulo = visualizacao === "acumulado" ? `Acumulado até ${MESES[mes - 1]}` : MESES[mes - 1];
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Nº Empenho</TableCell>
          <TableCell>Data</TableCell>
          <TableCell>Credor</TableCell>
          <TableCell>Histórico</TableCell>
          <TableCell align="right">Empenhado ({rotulo})</TableCell>
          <TableCell align="right">Liquidado ({rotulo})</TableCell>
          <TableCell align="right">Pago ({rotulo})</TableCell>
          <TableCell>Movimentação mensal</TableCell>
          <TableCell align="right">Ações</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {empenhosNoPeriodo.map((e) => {
          const valores = valoresDoEmpenhoNoPeriodo(e, mes, visualizacao);
          return (
            <TableRow key={e.id}>
              <TableCell>{e.numero}</TableCell>
              <TableCell>{formatarData(e.data_empenho)}</TableCell>
              <TableCell>{e.credor}</TableCell>
              <TableCell sx={{ maxWidth: 280, whiteSpace: "normal" }}>{e.historico}</TableCell>
              <TableCell align="right">{formatarMoeda(valores.empenhado)}</TableCell>
              <TableCell align="right">{formatarMoeda(valores.liquidado)}</TableCell>
              <TableCell align="right">{formatarMoeda(valores.pago)}</TableCell>
              <TableCell>
                {e.movimentos
                  .filter((m) => m.mes_referencia <= mes)
                  .sort((a, b) => a.mes_referencia - b.mes_referencia)
                  .map((m) => (
                    <Box
                      key={m.id}
                      sx={{
                        fontSize: "0.75rem",
                        color: "text.secondary",
                        fontWeight: m.mes_referencia === mes ? "bold" : undefined,
                      }}
                    >
                      {MESES[m.mes_referencia - 1]}: emp {formatarMoeda(m.valor_empenho_no_mes)} / liq{" "}
                      {formatarMoeda(m.valor_liquidado_no_mes)} / pago {formatarMoeda(m.valor_pago_no_mes)}
                    </Box>
                  ))}
              </TableCell>
              <TableCell align="right">
                <AcoesRegistroManual
                  item={e}
                  recurso="empenhos"
                  campos={CAMPOS_EDICAO_EMPENHO}
                  rotuloItem={`Empenho ${e.numero} (${e.credor})`}
                  onSalvo={onAlterado}
                />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

function LinhaRubrica({
  lancamento,
  visualizacao,
}: {
  lancamento: LancamentoExecucaoOrcamentaria;
  visualizacao: Visualizacao;
}) {
  const [aberto, setAberto] = useState(false);
  const [empenhos, setEmpenhos] = useState<Empenho[] | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [dialogoAberto, setDialogoAberto] = useState(false);
  const [novo, setNovo] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function carregarEmpenhos() {
    setCarregando(true);
    try {
      const { data } = await api.get<{ results: Empenho[] }>("/empenhos/", {
        params: { rubrica: lancamento.rubrica, page_size: 500 },
      });
      setEmpenhos(data.results);
    } finally {
      setCarregando(false);
    }
  }

  async function alternar() {
    const novoAberto = !aberto;
    setAberto(novoAberto);
    if (novoAberto && empenhos === null) {
      await carregarEmpenhos();
    }
  }

  async function salvarNovoEmpenho() {
    setSalvando(true);
    setErro(null);
    try {
      await api.post("/empenhos/", {
        unidade_gestora: lancamento.rubrica_detalhe.unidade_gestora,
        rubrica: lancamento.rubrica,
        numero: novo.numero,
        data_empenho: novo.data_empenho,
        credor: novo.credor,
        historico: novo.historico ?? "",
      });
      setDialogoAberto(false);
      setNovo({});
      await carregarEmpenhos();
    } catch {
      setErro("Não foi possível salvar. Confira os campos obrigatórios (Número e Data do Empenho).");
    } finally {
      setSalvando(false);
    }
  }

  const r = lancamento.rubrica_detalhe;
  const empenhado = visualizacao === "acumulado" ? lancamento.empenhado_acumulado : lancamento.empenhado_no_mes;
  const liquidado = visualizacao === "acumulado" ? lancamento.liquidado_acumulado : lancamento.liquidado_no_mes;
  const pago = visualizacao === "acumulado" ? lancamento.pago_acumulado : lancamento.pago_no_mes;

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={alternar}>
        <TableCell padding="checkbox">
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell>
          {r.orgao_nome} / {r.unidade_orcamentaria_nome}
        </TableCell>
        <TableCell>
          {r.funcao_codigo}.{r.subfuncao_codigo}.{r.programa_codigo}.{r.acao_codigo} - {r.acao_nome}
        </TableCell>
        <TableCell align="right">{formatarMoeda(lancamento.dotacao_atualizada)}</TableCell>
        <TableCell align="right">{formatarMoeda(empenhado)}</TableCell>
        <TableCell align="right">{formatarMoeda(liquidado)}</TableCell>
        <TableCell align="right">{formatarMoeda(pago)}</TableCell>
        <TableCell align="right">{formatarMoeda(lancamento.saldo_a_empenhar)}</TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={8} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1, flexWrap: "wrap" }}>
                <Typography variant="subtitle2">Detalhamento por empenho</Typography>
                <Typography variant="body2" color="text.secondary">
                  {r.unidade_gestora_nome} · {r.elemento_despesa_codigo} - {r.elemento_despesa_nome}
                </Typography>
                <Chip size="small" label={r.origem_dotacao_label} color={ORIGEM_COR[r.origem_dotacao]} />
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={(e) => {
                    e.stopPropagation();
                    setDialogoAberto(true);
                  }}
                  sx={{ ml: "auto" }}
                >
                  Novo Empenho
                </Button>
              </Box>
              <LinhaEmpenhos
                empenhos={empenhos}
                carregando={carregando}
                mes={lancamento.mes_referencia}
                visualizacao={visualizacao}
                onAlterado={carregarEmpenhos}
              />
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>

      <Dialog open={dialogoAberto} onClose={() => setDialogoAberto(false)} maxWidth="xs" fullWidth onClick={(e) => e.stopPropagation()}>
        <DialogTitle>
          Novo Empenho — {r.unidade_gestora_nome} / {r.elemento_despesa_codigo} - {r.elemento_despesa_nome}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {erro && <Alert severity="error">{erro}</Alert>}
          <TextField
            label="Número do Empenho"
            required
            value={novo.numero ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, numero: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Data do Empenho"
            type="date"
            required
            value={novo.data_empenho ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, data_empenho: e.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }}
            fullWidth
          />
          <TextField
            label="Credor"
            required
            value={novo.credor ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, credor: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Histórico"
            multiline
            minRows={2}
            value={novo.historico ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, historico: e.target.value }))}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogoAberto(false)}>Cancelar</Button>
          <Button variant="contained" disabled={salvando} onClick={salvarNovoEmpenho}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export function ExecucaoOrcamentariaPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  // 0 = ainda não sabemos qual é o último mês com movimento (ver efeito
  // abaixo) — nunca mostrado no Select, só evita buscar com o mês errado
  // enquanto isso não é descoberto.
  const [mes, setMes] = useState<number>(0);
  const [unidadesGestoras, setUnidadesGestoras] = useState<UnidadeGestora[]>([]);
  const [ugId, setUgId] = useState<number | "">("");
  const [visualizacao, setVisualizacao] = useState<Visualizacao>("acumulado");
  const [lancamentos, setLancamentos] = useState<LancamentoExecucaoOrcamentaria[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [pagina, setPagina] = useState(0);
  const [linhasPorPagina, setLinhasPorPagina] = useState(25);

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
  // exercício — nunca o mês corrente do calendário, que pode não ter
  // nenhum lançamento ainda (ex.: hoje é novembro mas só até setembro foi
  // processado).
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

  useEffect(() => {
    setPagina(0);
  }, [exercicioSelecionado, mes, ugId]);

  const lancamentosPaginados = useMemo(
    () => lancamentos.slice(pagina * linhasPorPagina, pagina * linhasPorPagina + linhasPorPagina),
    [lancamentos, pagina, linhasPorPagina]
  );

  const totais = useMemo(
    () =>
      lancamentos.reduce(
        (acc, l) => ({
          dotacao: acc.dotacao + Number(l.dotacao_atualizada),
          empenhado: acc.empenhado + Number(visualizacao === "acumulado" ? l.empenhado_acumulado : l.empenhado_no_mes),
          liquidado: acc.liquidado + Number(visualizacao === "acumulado" ? l.liquidado_acumulado : l.liquidado_no_mes),
          pago: acc.pago + Number(visualizacao === "acumulado" ? l.pago_acumulado : l.pago_no_mes),
        }),
        { dotacao: 0, empenhado: 0, liquidado: 0, pago: 0 }
      ),
    [lancamentos, visualizacao]
  );

  const rotuloPeriodo =
    visualizacao === "acumulado" ? `Acumulado até ${MESES[mes - 1]}` : `Movimento de ${MESES[mes - 1]}`;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Execução Orçamentária
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
            <MenuItem key={ug.id} value={ug.id}>
              {ug.nome}
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
        <CardResumo titulo="Dotação Atualizada" valor={totais.dotacao} />
        <CardResumo titulo={`Empenhado (${rotuloPeriodo})`} valor={totais.empenhado} cor="warning.main" />
        <CardResumo titulo={`Liquidado (${rotuloPeriodo})`} valor={totais.liquidado} cor="info.main" />
        <CardResumo titulo={`Pago (${rotuloPeriodo})`} valor={totais.pago} cor="success.main" />
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
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
            {!carregando && lancamentos.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  Nenhum lançamento para o período selecionado.
                </TableCell>
              </TableRow>
            )}
            {lancamentosPaginados.map((l) => (
              <LinhaRubrica key={l.id} lancamento={l} visualizacao={visualizacao} />
            ))}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={lancamentos.length}
          page={pagina}
          onPageChange={(_e, novaPagina) => setPagina(novaPagina)}
          rowsPerPage={linhasPorPagina}
          onRowsPerPageChange={(e) => {
            setLinhasPorPagina(Number(e.target.value));
            setPagina(0);
          }}
          rowsPerPageOptions={[10, 25, 50, 100]}
          labelRowsPerPage="Linhas por página"
          labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`}
        />
      </TableContainer>
    </Box>
  );
}
