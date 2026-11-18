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
import type { SaldoBalancoConta } from "../api/types";
import { useScope } from "../scope/ScopeContext";
import { AcoesRegistroManual, type CampoEdicao } from "../components/AcoesRegistroManual";

const CAMPOS_EDICAO: CampoEdicao[] = [
  { chave: "categoria", rotulo: "Categoria", tipo: "texto" },
  { chave: "codigo_conta", rotulo: "Código da Conta", tipo: "texto" },
  { chave: "banco", rotulo: "Banco", tipo: "texto" },
  { chave: "numero_conta", rotulo: "Número da Conta", tipo: "texto" },
  { chave: "apelido", rotulo: "Apelido", tipo: "texto" },
  { chave: "valor", rotulo: "Valor", tipo: "decimal" },
  {
    chave: "natureza",
    rotulo: "Natureza",
    tipo: "select",
    opcoes: [
      { value: "D", label: "Devedor" },
      { value: "C", label: "Credor" },
    ],
  },
];

function formatarMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarData(data: string): string {
  return new Date(`${data}T00:00:00`).toLocaleDateString("pt-BR");
}

// D (Devedor) soma positivo, C (Credor) soma negativo — convenção contábil
// padrão para conta de caixa/ativo: débito aumenta o saldo, crédito diminui.
function valorComSinal(valor: string, natureza: string): number {
  const n = Number(valor);
  return natureza === "C" ? -n : n;
}

interface GrupoUG {
  unidadeGestoraId: number;
  nome: string;
  total: number;
  contas: SaldoBalancoConta[];
}

function agruparPorUG(contas: SaldoBalancoConta[]): GrupoUG[] {
  const mapa = new Map<number, GrupoUG>();
  for (const c of contas) {
    if (!mapa.has(c.unidade_gestora)) {
      mapa.set(c.unidade_gestora, { unidadeGestoraId: c.unidade_gestora, nome: c.unidade_gestora_nome, total: 0, contas: [] });
    }
    const g = mapa.get(c.unidade_gestora)!;
    g.total += valorComSinal(c.valor, c.natureza);
    g.contas.push(c);
  }
  return Array.from(mapa.values()).sort((a, b) => b.total - a.total);
}

function LinhaConta({ conta, onAlterado }: { conta: SaldoBalancoConta; onAlterado: () => void }) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox" sx={{ pl: 4 }}>
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell>{conta.categoria}</TableCell>
        <TableCell>{conta.banco || "—"}</TableCell>
        <TableCell>
          {conta.numero_conta ? `${conta.numero_conta} ` : ""}({conta.apelido})
        </TableCell>
        <TableCell align="right">{formatarMoeda(Number(conta.valor))}</TableCell>
        <TableCell>
          <Chip
            size="small"
            label={conta.natureza === "D" ? "Devedor" : "Credor"}
            color={conta.natureza === "D" ? "success" : "warning"}
          />
        </TableCell>
        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
          <AcoesRegistroManual
            item={conta}
            recurso="saldo-balanco"
            campos={CAMPOS_EDICAO}
            rotuloItem={`${conta.categoria} - ${conta.numero_conta} (${conta.apelido})`}
            onSalvo={onAlterado}
          />
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={7} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
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
                            <Chip
                              size="small"
                              label={f.natureza === "D" ? "Devedor" : "Credor"}
                              color={f.natureza === "D" ? "success" : "warning"}
                            />
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
        <TableCell align="right" sx={{ fontWeight: "bold" }}>{formatarMoeda(grupo.total)}</TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={4} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox" />
                    <TableCell>Categoria</TableCell>
                    <TableCell>Banco</TableCell>
                    <TableCell>Conta</TableCell>
                    <TableCell align="right">Valor</TableCell>
                    <TableCell>Natureza</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.contas
                    .slice()
                    .sort((a, b) => Number(b.valor) - Number(a.valor))
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

export function SaldoBalancoPage() {
  const { municipioSelecionadoId } = useScope();
  const [contas, setContas] = useState<SaldoBalancoConta[]>([]);
  const [datasDisponiveis, setDatasDisponiveis] = useState<string[]>([]);
  const [dataSelecionada, setDataSelecionada] = useState<string>("");
  const [carregando, setCarregando] = useState(false);

  const [unidadesGestoras, setUnidadesGestoras] = useState<OpcaoSimples[]>([]);
  const [dialogoAberto, setDialogoAberto] = useState(false);
  const [novo, setNovo] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function recarregar() {
    if (!municipioSelecionadoId) return;
    setCarregando(true);
    buscarTodasPaginas<SaldoBalancoConta>("/saldo-balanco/", {})
      .then((todas) => {
        setContas(todas);
        const datas = Array.from(new Set(todas.map((c) => c.data_referencia))).sort();
        setDatasDisponiveis(datas);
        setDataSelecionada((atual) => atual || datas[datas.length - 1] || "");
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
      await api.post("/saldo-balanco/", {
        unidade_gestora: novo.unidade_gestora,
        data_referencia: novo.data_referencia,
        categoria: novo.categoria,
        codigo_conta: novo.codigo_conta,
        banco: novo.banco,
        numero_conta: novo.numero_conta,
        apelido: novo.apelido,
        valor: novo.valor || "0",
        natureza: novo.natureza || "D",
      });
      setDialogoAberto(false);
      setNovo({});
      recarregar();
    } catch {
      setErro(
        "Não foi possível salvar. Confira os campos obrigatórios (Unidade Gestora, Data de Referência, Categoria e Código da Conta)."
      );
    } finally {
      setSalvando(false);
    }
  }

  const contasNaData = useMemo(
    () => contas.filter((c) => c.data_referencia === dataSelecionada),
    [contas, dataSelecionada]
  );

  const grupos = useMemo(() => agruparPorUG(contasNaData), [contasNaData]);
  const totalGeral = useMemo(() => grupos.reduce((acc, g) => acc + g.total, 0), [grupos]);

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 2 }}>
        <Typography variant="h5">Saldo de Balanço</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogoAberto(true)}>
          Nova Conta
        </Button>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <Typography variant="body2">Data de referência:</Typography>
        <Select
          size="small"
          value={dataSelecionada}
          onChange={(e) => setDataSelecionada(e.target.value)}
          displayEmpty
          sx={{ minWidth: 160 }}
        >
          {datasDisponiveis.length === 0 && <MenuItem value="">Sem dados</MenuItem>}
          {datasDisponiveis.map((d) => (
            <MenuItem key={d} value={d}>
              {formatarData(d)}
            </MenuItem>
          ))}
        </Select>
      </Box>

      <Paper variant="outlined" sx={{ p: 2, mb: 3, maxWidth: 320 }}>
        <Typography variant="body2" color="text.secondary">
          Saldo Total ({grupos.length} {grupos.length === 1 ? "Unidade Gestora" : "Unidades Gestoras"})
        </Typography>
        <Typography variant="h6">{formatarMoeda(totalGeral)}</Typography>
      </Paper>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>Unidade Gestora</TableCell>
              <TableCell align="right">Contas</TableCell>
              <TableCell align="right">Saldo Total</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && grupos.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  Nenhum saldo de balanço importado.
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
        <DialogTitle>Nova Conta de Saldo de Balanço</DialogTitle>
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
            label="Data de Referência"
            type="date"
            required
            value={novo.data_referencia ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, data_referencia: e.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }}
            fullWidth
          />
          <TextField
            label="Categoria"
            required
            placeholder="Banco / Depósitos de diversas origens / Consignações"
            value={novo.categoria ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, categoria: e.target.value }))}
            fullWidth
          />
          <TextField
            label="Código da Conta"
            required
            value={novo.codigo_conta ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, codigo_conta: e.target.value }))}
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
            label="Valor"
            type="number"
            value={novo.valor ?? ""}
            onChange={(e) => setNovo((f) => ({ ...f, valor: e.target.value }))}
            fullWidth
          />
          <TextField
            select
            label="Natureza"
            required
            value={novo.natureza ?? "D"}
            onChange={(e) => setNovo((f) => ({ ...f, natureza: e.target.value }))}
            fullWidth
          >
            <MenuItem value="D">Devedor</MenuItem>
            <MenuItem value="C">Credor</MenuItem>
          </TextField>
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
