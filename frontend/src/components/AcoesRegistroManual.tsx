import { useState } from "react";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  TextField,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { api } from "../api/client";
import type { CampoOrigemRegistro } from "../api/types";

export interface CampoEdicao {
  chave: string;
  rotulo: string;
  tipo?: "decimal" | "select" | "texto" | "data";
  opcoes?: { value: string; label: string }[];
}

interface Props<T extends CampoOrigemRegistro & { id: number }> {
  item: T;
  recurso: string;
  campos: CampoEdicao[];
  rotuloItem: string;
  onSalvo: () => void;
}

// Ações compartilhadas de editar/excluir para os "fatos" importados que
// ganharam CRUD (ver CLAUDE.md "CRUD completo + auditoria + agregados").
// Só os campos realmente corrigíveis (valores/flags) entram em `campos` —
// a classificação (órgão, fonte, rubrica em si) não é editável aqui, só o
// valor que pode estar errado na importação.
export function AcoesRegistroManual<T extends CampoOrigemRegistro & { id: number }>({
  item,
  recurso,
  campos,
  rotuloItem,
  onSalvo,
}: Props<T>) {
  const [aberto, setAberto] = useState(false);
  const [formulario, setFormulario] = useState<Record<string, unknown>>({});
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function abrir() {
    const registro = item as unknown as Record<string, unknown>;
    setFormulario(Object.fromEntries(campos.map((c) => [c.chave, registro[c.chave]])));
    setErro(null);
    setAberto(true);
  }

  async function salvar() {
    setSalvando(true);
    try {
      await api.patch(`/${recurso}/${item.id}/`, formulario);
      setAberto(false);
      onSalvo();
    } catch {
      setErro("Não foi possível salvar. Confira os valores informados.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir() {
    if (!window.confirm(`Excluir "${rotuloItem}"? Esta ação não pode ser desfeita.`)) return;
    try {
      await api.delete(`/${recurso}/${item.id}/`);
      onSalvo();
    } catch {
      window.alert("Não foi possível excluir este registro (pode estar em uso por outro registro).");
    }
  }

  return (
    <>
      <IconButton size="small" onClick={abrir} title="Editar">
        <EditIcon fontSize="small" />
      </IconButton>
      <IconButton size="small" onClick={excluir} title="Excluir">
        <DeleteIcon fontSize="small" />
      </IconButton>

      <Dialog open={aberto} onClose={() => setAberto(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Editar — {rotuloItem}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {item.origem_registro === "IMPORTADO" && (
            <Alert severity="warning">
              Este registro veio de uma importação. Editar aqui não altera o arquivo de origem — uma nova
              importação do mesmo relatório pode sobrescrever esta correção.
            </Alert>
          )}
          {erro && <Alert severity="error">{erro}</Alert>}
          {campos.map((c) =>
            c.tipo === "select" ? (
              <TextField
                key={c.chave}
                select
                label={c.rotulo}
                value={formulario[c.chave] ?? ""}
                onChange={(e) => setFormulario((f) => ({ ...f, [c.chave]: e.target.value }))}
                fullWidth
              >
                {(c.opcoes ?? []).map((o) => (
                  <MenuItem key={o.value} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
              </TextField>
            ) : (
              <TextField
                key={c.chave}
                label={c.rotulo}
                type={c.tipo === "texto" ? "text" : c.tipo === "data" ? "date" : "number"}
                value={formulario[c.chave] ?? ""}
                onChange={(e) => setFormulario((f) => ({ ...f, [c.chave]: e.target.value }))}
                slotProps={c.tipo === "data" ? { inputLabel: { shrink: true } } : undefined}
                fullWidth
              />
            )
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAberto(false)}>Cancelar</Button>
          <Button variant="contained" disabled={salvando} onClick={salvar}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
