import { useEffect, useState } from "react";
import {
  Alert,
  FormControlLabel,
  Paper,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Typography,
} from "@mui/material";
import { api } from "../../api/client";
import type { Parametro } from "../../api/types";
import { useParametros } from "../../parametros/ParametrosContext";

// Sem create/delete de propósito — os parâmetros são predefinidos pelo
// sistema (ver `apps.parametros.models.Parametro`), por isso uma página
// própria em vez do `CrudManager` genérico (que sempre oferece "Novo"/
// excluir). Só o valor de cada um é editável, por um Switch direto na linha.
export function ParametrosPage() {
  const [parametros, setParametros] = useState<Parametro[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const { recarregar: recarregarContexto } = useParametros();

  function carregar() {
    api.get<{ results: Parametro[] }>("/parametros/").then(({ data }) => setParametros(data.results));
  }

  useEffect(() => {
    carregar();
  }, []);

  async function alternar(p: Parametro) {
    setErro(null);
    try {
      await api.patch(`/parametros/${p.chave}/`, { valor_booleano: !p.valor_booleano });
      carregar();
      recarregarContexto();
    } catch {
      setErro("Não foi possível salvar — confira se você tem permissão de equipe do escritório.");
    }
  }

  return (
    <>
      <Typography variant="h5" gutterBottom>
        Parâmetros
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Configurações globais da interface, válidas para todos os usuários do sistema.
      </Typography>

      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>
          {erro}
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableBody>
            {parametros.length === 0 && (
              <TableRow>
                <TableCell>Nenhum parâmetro cadastrado.</TableCell>
              </TableRow>
            )}
            {parametros.map((p) => (
              <TableRow key={p.chave}>
                <TableCell>
                  <FormControlLabel
                    control={<Switch checked={p.valor_booleano} onChange={() => alternar(p)} />}
                    label={p.descricao}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
