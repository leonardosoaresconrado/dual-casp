import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
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
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import BarChartIcon from "@mui/icons-material/BarChart";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { useNavigate } from "react-router-dom";
import { api, buscarTodasPaginas } from "../api/client";
import type { RestoAPagar } from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { AcoesRegistroManual, type CampoEdicao } from "../components/AcoesRegistroManual";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

const CAMPOS_EDICAO: CampoEdicao[] = [
  { chave: "exercicio_origem", rotulo: "Exercício de Origem", tipo: "decimal" },
  { chave: "numero_empenho", rotulo: "Número do Empenho", tipo: "texto" },
  { chave: "credor_nome", rotulo: "Credor", tipo: "texto" },
  { chave: "inscricao_processada", rotulo: "Inscrição Processada", tipo: "decimal" },
  { chave: "inscricao_nao_processada", rotulo: "Inscrição Não Processada", tipo: "decimal" },
  { chave: "reinscricao", rotulo: "Reinscrição", tipo: "decimal" },
  { chave: "cancelamento", rotulo: "Cancelamento", tipo: "decimal" },
  { chave: "liquidacao", rotulo: "Liquidação", tipo: "decimal" },
  { chave: "rpp_pago", rotulo: "RPP Pago", tipo: "decimal" },
  { chave: "rpnp_pago", rotulo: "RPNP Pago", tipo: "decimal" },
];

function formatarMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// Saldo ainda pendente de pagamento: tudo que foi inscrito/reinscrito,
// menos o que foi cancelado, menos o que já foi pago (RPP + RPNP) — não
// distingue o "balde" processado/não-processado internamente, só o total.
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

type Dimensao = "unidade_gestora" | "fonte" | "exercicio_origem" | "orgao" | "elemento_despesa";

const DIMENSOES: { valor: Dimensao; rotulo: string }[] = [
  { valor: "unidade_gestora", rotulo: "Unidade Gestora" },
  { valor: "fonte", rotulo: "Fonte de Recursos" },
  { valor: "exercicio_origem", rotulo: "Exercício de Origem" },
  { valor: "orgao", rotulo: "Órgão" },
  { valor: "elemento_despesa", rotulo: "Elemento de Despesa" },
];

// Órgão/elemento_despesa podem ser null — um handful de empenhos 2020/2021
// não foi enriquecido (ver `enriquecer_restos_a_pagar` no CLAUDE.md),
// então entram num grupo "(sem órgão)"/"(sem elemento)" em vez de sumirem
// da listagem.
function chaveEDimensao(r: RestoAPagar, dimensao: Dimensao): { chave: string; rotulo: string } {
  switch (dimensao) {
    case "unidade_gestora":
      return { chave: String(r.unidade_gestora), rotulo: r.unidade_gestora_nome };
    case "fonte":
      return { chave: String(r.fonte_recursos), rotulo: `${r.fonte_recursos_codigo} - ${r.fonte_recursos_nome}` };
    case "exercicio_origem":
      return { chave: String(r.exercicio_origem), rotulo: String(r.exercicio_origem) };
    case "orgao":
      return { chave: r.orgao ? String(r.orgao) : "__sem_orgao__", rotulo: r.orgao_nome || "(sem órgão)" };
    case "elemento_despesa":
      return {
        chave: r.elemento_despesa ? String(r.elemento_despesa) : "__sem_elemento__",
        rotulo: r.elemento_despesa ? `${r.elemento_despesa_codigo} - ${r.elemento_despesa_nome}` : "(sem elemento)",
      };
  }
}

interface Grupo {
  chave: string;
  rotulo: string;
  totalInscrito: number;
  totalPago: number;
  totalSaldo: number;
  restos: RestoAPagar[];
}

function agrupar(restos: RestoAPagar[], dimensao: Dimensao): Grupo[] {
  const mapa = new Map<string, Grupo>();

  for (const r of restos) {
    const { chave, rotulo } = chaveEDimensao(r, dimensao);
    if (!mapa.has(chave)) {
      mapa.set(chave, { chave, rotulo, totalInscrito: 0, totalPago: 0, totalSaldo: 0, restos: [] });
    }
    const g = mapa.get(chave)!;
    const inscrito = Number(r.inscricao_processada) + Number(r.inscricao_nao_processada) + Number(r.reinscricao);
    const pago = Number(r.rpp_pago) + Number(r.rpnp_pago);
    g.totalInscrito += inscrito;
    g.totalPago += pago;
    g.totalSaldo += saldoAPagar(r);
    g.restos.push(r);
  }

  return Array.from(mapa.values()).sort((a, b) => b.totalSaldo - a.totalSaldo);
}

function LinhaGrupo({ grupo, onAlterado }: { grupo: Grupo; onAlterado: () => void }) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox">
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell sx={{ fontWeight: "bold" }}>{grupo.rotulo}</TableCell>
        <TableCell align="right">{grupo.restos.length}</TableCell>
        <TableCell align="right">{formatarMoeda(grupo.totalInscrito)}</TableCell>
        <TableCell align="right">{formatarMoeda(grupo.totalPago)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.totalSaldo)}</TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={6} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 2, overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Exercício</TableCell>
                    <TableCell>Nº Empenho</TableCell>
                    <TableCell>Credor</TableCell>
                    <TableCell align="right">Insc. Processada</TableCell>
                    <TableCell align="right">Insc. Não Processada</TableCell>
                    <TableCell align="right">Reinscrição</TableCell>
                    <TableCell align="right">Cancelamento</TableCell>
                    <TableCell align="right">Liquidação</TableCell>
                    <TableCell align="right">RPP Pago</TableCell>
                    <TableCell align="right">RPNP Pago</TableCell>
                    <TableCell align="right">Saldo a Pagar</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.restos
                    .slice()
                    .sort((a, b) => saldoAPagar(b) - saldoAPagar(a))
                    .map((r) => (
                      <TableRow key={r.id}>
                        <TableCell>{r.exercicio_origem}</TableCell>
                        <TableCell>
                          {r.numero_empenho}
                          {(r.orgao_nome || r.elemento_despesa_nome) && (
                            <Typography variant="caption" sx={{ display: "block" }} color="text.secondary">
                              {[
                                r.orgao_nome,
                                r.elemento_despesa_nome &&
                                  `${r.classificacao_economica_codigo || r.elemento_despesa_codigo} - ${r.elemento_despesa_nome}`,
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>{r.credor_nome || "—"}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(r.inscricao_processada))}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(r.inscricao_nao_processada))}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(r.reinscricao))}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(r.cancelamento))}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(r.liquidacao))}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(r.rpp_pago))}</TableCell>
                        <TableCell align="right">{formatarMoeda(Number(r.rpnp_pago))}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(saldoAPagar(r))}</TableCell>
                        <TableCell align="right">
                          <AcoesRegistroManual
                            item={r}
                            recurso="restos-a-pagar"
                            campos={CAMPOS_EDICAO}
                            rotuloItem={`Empenho ${r.numero_empenho} (${r.exercicio_origem})`}
                            onSalvo={onAlterado}
                          />
                        </TableCell>
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

interface OpcaoSimples {
  id: number;
  label: string;
}

export function RestosAPagarPage() {
  const navigate = useNavigate();
  const { municipioSelecionadoId } = useScope();
  const [restos, setRestos] = useState<RestoAPagar[]>([]);
  const [mesesDisponiveis, setMesesDisponiveis] = useState<number[]>([]);
  const [mesSelecionado, setMesSelecionado] = useState<number | "">("");
  const [carregando, setCarregando] = useState(false);
  const [dimensao, setDimensao] = useState<Dimensao>("unidade_gestora");
  const [filtroDimensao, setFiltroDimensao] = useState<Dimensao | "">("");
  const [filtroValor, setFiltroValor] = useState<string>("");

  const [unidadesGestoras, setUnidadesGestoras] = useState<OpcaoSimples[]>([]);
  const [fontes, setFontes] = useState<OpcaoSimples[]>([]);
  const [dialogoAberto, setDialogoAberto] = useState(false);
  const [novo, setNovo] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function recarregar() {
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
  }

  useEffect(() => {
    recarregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [municipioSelecionadoId]);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get("/unidades-gestoras/", { params: { municipio: municipioSelecionadoId, page_size: 50 } })
      .then(({ data }) => {
        setUnidadesGestoras(
          (data.results ?? data).map((u: { id: number; nome: string }) => ({ id: u.id, label: u.nome }))
        );
      });
  }, [municipioSelecionadoId]);

  useEffect(() => {
    // Fonte de Recursos é um catálogo nacional, sem escopo de UG — uma
    // única lista global, carregada uma vez (mesmo padrão de
    // unidadesGestoras acima, sem depender de qual UG está selecionada
    // no formulário).
    api.get("/fontes-recursos/", { params: { page_size: 200 } }).then(({ data }) => {
      setFontes(
        (data.results ?? data).map((fr: { id: number; codigo: string; nome: string }) => ({
          id: fr.id,
          label: `${fr.codigo} - ${fr.nome}`,
        }))
      );
    });
  }, []);

  async function salvarNovo() {
    setSalvando(true);
    setErro(null);
    try {
      await api.post("/restos-a-pagar/", {
        unidade_gestora: novo.unidade_gestora,
        fonte_recursos: novo.fonte_recursos,
        mes_referencia: novo.mes_referencia,
        exercicio_origem: novo.exercicio_origem,
        numero_empenho: novo.numero_empenho,
        credor_nome: novo.credor_nome || "",
        inscricao_processada: novo.inscricao_processada || "0",
        inscricao_nao_processada: novo.inscricao_nao_processada || "0",
        reinscricao: novo.reinscricao || "0",
        cancelamento: novo.cancelamento || "0",
        liquidacao: novo.liquidacao || "0",
        rpp_pago: novo.rpp_pago || "0",
        rpnp_pago: novo.rpnp_pago || "0",
      });
      setDialogoAberto(false);
      setNovo({});
      recarregar();
    } catch {
      setErro("Não foi possível salvar. Confira os campos obrigatórios (Unidade Gestora, Fonte, Mês, Exercício e Número do Empenho).");
    } finally {
      setSalvando(false);
    }
  }

  const restosNoMes = useMemo(() => restos.filter((r) => r.mes_referencia === mesSelecionado), [restos, mesSelecionado]);

  // Opções do "Filtrar por" = valores distintos da dimensão escolhida,
  // tirados dos restos já carregados no mês (client-side, mesmo padrão do
  // "Agrupar por" — sem chamada nova ao backend).
  const opcoesFiltro = useMemo(() => {
    if (!filtroDimensao) return [];
    const mapa = new Map<string, string>();
    for (const r of restosNoMes) {
      const { chave, rotulo } = chaveEDimensao(r, filtroDimensao);
      if (!mapa.has(chave)) mapa.set(chave, rotulo);
    }
    return Array.from(mapa, ([chave, rotulo]) => ({ chave, rotulo })).sort((a, b) => a.rotulo.localeCompare(b.rotulo));
  }, [restosNoMes, filtroDimensao]);

  const restosFiltrados = useMemo(() => {
    if (!filtroDimensao || !filtroValor) return restosNoMes;
    return restosNoMes.filter((r) => chaveEDimensao(r, filtroDimensao).chave === filtroValor);
  }, [restosNoMes, filtroDimensao, filtroValor]);

  const grupos = useMemo(() => agrupar(restosFiltrados, dimensao), [restosFiltrados, dimensao]);
  const totais = useMemo(
    () =>
      grupos.reduce(
        (acc, g) => ({
          inscrito: acc.inscrito + g.totalInscrito,
          pago: acc.pago + g.totalPago,
          saldo: acc.saldo + g.totalSaldo,
        }),
        { inscrito: 0, pago: 0, saldo: 0 }
      ),
    [grupos]
  );
  const rotuloDimensao = DIMENSOES.find((d) => d.valor === dimensao)?.rotulo ?? "";

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 2 }}>
        <Typography variant="h5">Restos a Pagar</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button variant="outlined" startIcon={<BarChartIcon />} onClick={() => navigate("/relatorios/restos-a-pagar/graficos")}>
            Ver Gráficos
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogoAberto(true)}>
            Novo Resto a Pagar
          </Button>
        </Box>
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
            <MenuItem key={m} value={m}>
              {MESES[m - 1]}
            </MenuItem>
          ))}
        </Select>

        <Select size="small" value={dimensao} onChange={(e) => setDimensao(e.target.value as Dimensao)} sx={{ minWidth: 220 }}>
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
          sx={{ minWidth: 220 }}
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
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 200, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Inscrito + Reinscrito
          </Typography>
          <Typography variant="h6">{formatarMoeda(totais.inscrito)}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 200, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Pago (RPP + RPNP)
          </Typography>
          <Typography variant="h6" color="success.main">
            {formatarMoeda(totais.pago)}
          </Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 200, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Saldo a Pagar
          </Typography>
          <Typography variant="h6" color="warning.main">
            {formatarMoeda(totais.saldo)}
          </Typography>
        </Paper>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>{rotuloDimensao}</TableCell>
              <TableCell align="right">Empenhos</TableCell>
              <TableCell align="right">Inscrito + Reinscrito</TableCell>
              <TableCell align="right">Pago (RPP + RPNP)</TableCell>
              <TableCell align="right">Saldo a Pagar</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && grupos.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  Nenhum resto a pagar importado.
                </TableCell>
              </TableRow>
            )}
            {grupos.map((g) => (
              <LinhaGrupo key={g.chave} grupo={g} onAlterado={recarregar} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogoAberto} onClose={() => setDialogoAberto(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Novo Resto a Pagar</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {erro && <Alert severity="error">{erro}</Alert>}
          <TextField
            select
            label="Unidade Gestora"
            required
            value={novo.unidade_gestora ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, unidade_gestora: e.target.value }))}
            fullWidth
          >
            {unidadesGestoras.map((ug) => (
              <MenuItem key={ug.id} value={ug.id}>
                {ug.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Fonte de Recursos"
            required
            value={novo.fonte_recursos ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, fonte_recursos: e.target.value }))}
            fullWidth
          >
            {fontes.map((fr) => (
              <MenuItem key={fr.id} value={fr.id}>
                {fr.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Mês de Referência"
            required
            value={novo.mes_referencia ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, mes_referencia: e.target.value }))}
            fullWidth
          >
            {MESES.map((nome, idx) => (
              <MenuItem key={nome} value={idx + 1}>
                {nome}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Exercício de Origem"
            type="number"
            required
            value={novo.exercicio_origem ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, exercicio_origem: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Número do Empenho"
            required
            value={novo.numero_empenho ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, numero_empenho: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Credor"
            value={novo.credor_nome ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, credor_nome: e.target.value }))}
            fullWidth
          />
          {CAMPOS_EDICAO.filter((c) => c.tipo === "decimal" && c.chave !== "exercicio_origem").map((c) => (
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
