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
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { api, buscarTodasPaginas } from "../api/client";
import type { SaldoContaBancaria } from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { AcoesRegistroManual, type CampoEdicao } from "../components/AcoesRegistroManual";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

const CAMPOS_EDICAO: CampoEdicao[] = [
  { chave: "banco", rotulo: "Banco", tipo: "texto" },
  { chave: "numero_conta", rotulo: "Número da Conta", tipo: "texto" },
  { chave: "apelido", rotulo: "Apelido", tipo: "texto" },
  { chave: "saldo_pre_pagamentos_previstos", rotulo: "Saldo Pré-Pagamentos Previstos", tipo: "decimal" },
  { chave: "saldo_nao_comprometido", rotulo: "Saldo Não Comprometido", tipo: "decimal" },
];

function formatarMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface GrupoUG {
  unidadeGestoraId: number;
  nome: string;
  totalPrevisto: number;
  totalNaoComprometido: number;
  contas: SaldoContaBancaria[];
}

function agruparPorUG(contas: SaldoContaBancaria[]): GrupoUG[] {
  const mapa = new Map<number, GrupoUG>();
  for (const c of contas) {
    if (!mapa.has(c.unidade_gestora)) {
      mapa.set(c.unidade_gestora, {
        unidadeGestoraId: c.unidade_gestora,
        nome: c.unidade_gestora_nome,
        totalPrevisto: 0,
        totalNaoComprometido: 0,
        contas: [],
      });
    }
    const g = mapa.get(c.unidade_gestora)!;
    g.totalPrevisto += Number(c.saldo_pre_pagamentos_previstos);
    g.totalNaoComprometido += Number(c.saldo_nao_comprometido);
    g.contas.push(c);
  }
  return Array.from(mapa.values()).sort((a, b) => b.totalNaoComprometido - a.totalNaoComprometido);
}

function LinhaConta({ conta, onAlterado }: { conta: SaldoContaBancaria; onAlterado: () => void }) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox" sx={{ pl: 4 }}>
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell>{conta.banco}</TableCell>
        <TableCell>
          {conta.numero_conta} ({conta.apelido})
        </TableCell>
        <TableCell align="right">{formatarMoeda(Number(conta.saldo_pre_pagamentos_previstos))}</TableCell>
        <TableCell align="right">{formatarMoeda(Number(conta.saldo_nao_comprometido))}</TableCell>
        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
          <AcoesRegistroManual
            item={conta}
            recurso="saldo-conta-bancaria"
            campos={CAMPOS_EDICAO}
            rotuloItem={`${conta.banco} - ${conta.numero_conta} (${conta.apelido})`}
            onSalvo={onAlterado}
          />
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={6} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 2, ml: 6 }}>
              {conta.fontes.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Nenhuma fonte de recursos para esta conta.
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Fonte de Recursos</TableCell>
                      <TableCell align="right">Valor</TableCell>
                      <TableCell>Natureza</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {conta.fontes
                      .slice()
                      .sort((a, b) => Number(b.valor) - Number(a.valor))
                      .map((f) => (
                        <TableRow key={f.id}>
                          <TableCell>
                            {f.fonte_recursos_codigo} - {f.fonte_recursos_nome}
                          </TableCell>
                          <TableCell align="right">{formatarMoeda(Number(f.valor))}</TableCell>
                          <TableCell>
                            {f.natureza && (
                              <Chip
                                size="small"
                                label={f.natureza === "D" ? "Devedor" : "Credor"}
                                color={f.natureza === "D" ? "success" : "warning"}
                              />
                            )}
                          </TableCell>
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

function LinhaUG({ grupo, onAlterado }: { grupo: GrupoUG; onAlterado: () => void }) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox">
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell sx={{ fontWeight: "bold" }}>{grupo.nome}</TableCell>
        <TableCell align="right">{grupo.contas.length}</TableCell>
        <TableCell align="right">{formatarMoeda(grupo.totalPrevisto)}</TableCell>
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.totalNaoComprometido)}</TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={5} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox" />
                    <TableCell>Banco</TableCell>
                    <TableCell>Conta</TableCell>
                    <TableCell align="right">Saldo Pré-Pagamentos Previstos</TableCell>
                    <TableCell align="right">Saldo Não Comprometido</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.contas
                    .slice()
                    .sort((a, b) => Number(b.saldo_nao_comprometido) - Number(a.saldo_nao_comprometido))
                    .map((c) => (
                      <LinhaConta key={c.id} conta={c} onAlterado={onAlterado} />
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

export function SaldoContaBancariaPage() {
  const { municipioSelecionadoId } = useScope();
  const [contas, setContas] = useState<SaldoContaBancaria[]>([]);
  const [mesesDisponiveis, setMesesDisponiveis] = useState<number[]>([]);
  const [mesSelecionado, setMesSelecionado] = useState<number | "">("");
  const [carregando, setCarregando] = useState(false);

  const [unidadesGestoras, setUnidadesGestoras] = useState<OpcaoSimples[]>([]);
  const [dialogoAberto, setDialogoAberto] = useState(false);
  const [novo, setNovo] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function recarregar() {
    if (!municipioSelecionadoId) return;
    setCarregando(true);
    buscarTodasPaginas<SaldoContaBancaria>("/saldo-conta-bancaria/", {})
      .then((todas) => {
        setContas(todas);
        const meses = Array.from(new Set(todas.map((c) => c.mes_referencia))).sort((a, b) => a - b);
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

  async function salvarNovo() {
    setSalvando(true);
    setErro(null);
    try {
      await api.post("/saldo-conta-bancaria/", {
        unidade_gestora: novo.unidade_gestora,
        mes_referencia: novo.mes_referencia,
        data_referencia: novo.data_referencia,
        banco: novo.banco,
        numero_conta: novo.numero_conta,
        apelido: novo.apelido,
        saldo_pre_pagamentos_previstos: novo.saldo_pre_pagamentos_previstos || "0",
        saldo_nao_comprometido: novo.saldo_nao_comprometido || "0",
      });
      setDialogoAberto(false);
      setNovo({});
      recarregar();
    } catch {
      setErro(
        "Não foi possível salvar. Confira os campos obrigatórios (Unidade Gestora, Mês, Data de Referência e Número da Conta)."
      );
    } finally {
      setSalvando(false);
    }
  }

  const contasNoMes = useMemo(
    () => contas.filter((c) => c.mes_referencia === mesSelecionado),
    [contas, mesSelecionado]
  );

  const grupos = useMemo(() => agruparPorUG(contasNoMes), [contasNoMes]);
  const totais = useMemo(
    () =>
      grupos.reduce(
        (acc, g) => ({
          previsto: acc.previsto + g.totalPrevisto,
          naoComprometido: acc.naoComprometido + g.totalNaoComprometido,
        }),
        { previsto: 0, naoComprometido: 0 }
      ),
    [grupos]
  );

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 2 }}>
        <Typography variant="h5">Saldo por Conta Bancária</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogoAberto(true)}>
          Nova Conta Bancária
        </Button>
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
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 220, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Saldo Pré-Pagamentos Previstos
          </Typography>
          <Typography variant="h6">{formatarMoeda(totais.previsto)}</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, minWidth: 220, flex: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Saldo Não Comprometido
          </Typography>
          <Typography variant="h6" color="success.main">
            {formatarMoeda(totais.naoComprometido)}
          </Typography>
        </Paper>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>Unidade Gestora</TableCell>
              <TableCell align="right">Contas</TableCell>
              <TableCell align="right">Saldo Pré-Pagamentos Previstos</TableCell>
              <TableCell align="right">Saldo Não Comprometido</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && grupos.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  Nenhum saldo por conta bancária importado.
                </TableCell>
              </TableRow>
            )}
            {grupos.map((g) => (
              <LinhaUG key={g.unidadeGestoraId} grupo={g} onAlterado={recarregar} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogoAberto} onClose={() => setDialogoAberto(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Nova Conta Bancária</DialogTitle>
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
            label="Data de Referência"
            type="date"
            required
            value={novo.data_referencia ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, data_referencia: e.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }}
            fullWidth
          />
          <TextField
            label="Banco"
            value={novo.banco ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, banco: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Número da Conta"
            required
            value={novo.numero_conta ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, numero_conta: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Apelido"
            value={novo.apelido ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, apelido: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Saldo Pré-Pagamentos Previstos"
            type="number"
            value={novo.saldo_pre_pagamentos_previstos ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, saldo_pre_pagamentos_previstos: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Saldo Não Comprometido"
            type="number"
            value={novo.saldo_nao_comprometido ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, saldo_nao_comprometido: e.target.value }))}
            fullWidth
          />
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
