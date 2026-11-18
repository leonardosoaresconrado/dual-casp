import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
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
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { api } from "../api/client";

export interface OpcaoCampo {
  value: string | number;
  label: string;
}

export interface CampoFormulario {
  chave: string;
  rotulo: string;
  tipo?: "texto" | "numero" | "decimal" | "data" | "select" | "textarea" | "booleano" | "senha";
  opcoes?: OpcaoCampo[];
  obrigatorio?: boolean;
  somenteColuna?: boolean;
}

export interface ColunaExtra {
  chave: string;
  rotulo: string;
  render: (item: Record<string, unknown>) => React.ReactNode;
}

interface CrudManagerProps {
  titulo: string;
  recurso: string;
  campos: CampoFormulario[];
  colunasExtras?: ColunaExtra[];
  parametrosExtras?: Record<string, string | number | undefined>;
  valoresPadrao?: Record<string, unknown>;
  dependenciasRecarregar?: unknown[];
}

export function CrudManager({
  titulo,
  recurso,
  campos,
  colunasExtras = [],
  parametrosExtras = {},
  valoresPadrao = {},
  dependenciasRecarregar = [],
}: CrudManagerProps) {
  const [itens, setItens] = useState<Record<string, unknown>[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [dialogoAberto, setDialogoAberto] = useState(false);
  const [editando, setEditando] = useState<Record<string, unknown> | null>(null);
  const [formulario, setFormulario] = useState<Record<string, unknown>>({});
  const [salvando, setSalvando] = useState(false);

  const paramsChave = JSON.stringify(parametrosExtras);

  async function carregar() {
    setCarregando(true);
    try {
      const { data } = await api.get(`/${recurso}/`, {
        params: { page_size: 500, ...parametrosExtras },
      });
      setItens(data.results ?? data);
      setErro(null);
    } catch {
      setErro("Não foi possível carregar os dados.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsChave, ...dependenciasRecarregar]);

  function abrirNovo() {
    setEditando(null);
    setFormulario({ ...valoresPadrao, ...parametrosExtras });
    setDialogoAberto(true);
  }

  function abrirEdicao(item: Record<string, unknown>) {
    setEditando(item);
    setFormulario({ ...item });
    setDialogoAberto(true);
  }

  async function salvar() {
    setSalvando(true);
    try {
      if (editando) {
        await api.patch(`/${recurso}/${editando.id}/`, formulario);
      } else {
        await api.post(`/${recurso}/`, formulario);
      }
      setDialogoAberto(false);
      await carregar();
    } catch {
      setErro("Não foi possível salvar. Confira os campos obrigatórios.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item: Record<string, unknown>) {
    if (!window.confirm("Excluir este registro?")) return;
    try {
      await api.delete(`/${recurso}/${item.id}/`);
      await carregar();
    } catch {
      setErro("Não foi possível excluir este registro (pode estar em uso).");
    }
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5">{titulo}</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={abrirNovo}>
          Novo
        </Button>
      </Box>

      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>
          {erro}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {campos.map((c) => (
                <TableCell key={c.chave}>{c.rotulo}</TableCell>
              ))}
              {colunasExtras.map((c) => (
                <TableCell key={c.chave}>{c.rotulo}</TableCell>
              ))}
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && itens.length === 0 && (
              <TableRow>
                <TableCell colSpan={campos.length + colunasExtras.length + 1} align="center">
                  Nenhum registro cadastrado.
                </TableCell>
              </TableRow>
            )}
            {itens.map((item) => (
              <TableRow key={String(item.id)}>
                {campos.map((c) => (
                  <TableCell key={c.chave}>
                    {c.tipo === "select"
                      ? c.opcoes?.find((o) => o.value === item[c.chave])?.label ?? String(item[c.chave] ?? "")
                      : c.tipo === "booleano"
                      ? (item[c.chave] ? "Sim" : "Não")
                      : String(item[c.chave] ?? "")}
                  </TableCell>
                ))}
                {colunasExtras.map((c) => (
                  <TableCell key={c.chave}>{c.render(item)}</TableCell>
                ))}
                <TableCell align="right">
                  <IconButton size="small" onClick={() => abrirEdicao(item)}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => excluir(item)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogoAberto} onClose={() => setDialogoAberto(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editando ? "Editar" : "Novo"} registro</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {campos.filter((campo) => !campo.somenteColuna).map((campo) => {
            const valor = formulario[campo.chave] ?? "";
            if (campo.tipo === "booleano") {
              return (
                <FormControlLabel
                  key={campo.chave}
                  control={
                    <Checkbox
                      checked={Boolean(valor)}
                      onChange={(e) => setFormulario((f) => ({ ...f, [campo.chave]: e.target.checked }))}
                    />
                  }
                  label={campo.rotulo}
                />
              );
            }
            if (campo.tipo === "select") {
              return (
                <TextField
                  key={campo.chave}
                  select
                  label={campo.rotulo}
                  value={valor}
                  required={campo.obrigatorio}
                  onChange={(e) => setFormulario((f) => ({ ...f, [campo.chave]: e.target.value }))}
                  fullWidth
                >
                  {(campo.opcoes ?? []).map((o) => (
                    <MenuItem key={o.value} value={o.value}>
                      {o.label}
                    </MenuItem>
                  ))}
                </TextField>
              );
            }
            return (
              <TextField
                key={campo.chave}
                label={campo.rotulo}
                type={
                  campo.tipo === "numero" || campo.tipo === "decimal"
                    ? "number"
                    : campo.tipo === "data"
                    ? "date"
                    : campo.tipo === "senha"
                    ? "password"
                    : "text"
                }
                multiline={campo.tipo === "textarea"}
                minRows={campo.tipo === "textarea" ? 3 : undefined}
                value={valor}
                required={campo.obrigatorio}
                slotProps={campo.tipo === "data" ? { inputLabel: { shrink: true } } : undefined}
                onChange={(e) => setFormulario((f) => ({ ...f, [campo.chave]: e.target.value }))}
                fullWidth
              />
            );
          })}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogoAberto(false)}>Cancelar</Button>
          <Button variant="contained" onClick={salvar} disabled={salvando}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
