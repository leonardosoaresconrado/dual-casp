import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { api } from "../../api/client";
import type { Exercicio, RubricaReceita } from "../../api/types";
import { useScope } from "../../scope/ScopeContext";
import { useParametro } from "../../parametros/ParametrosContext";
import { AcoesRegistroManual, type CampoEdicao } from "../../components/AcoesRegistroManual";

function formatarMoeda(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const CAMPOS_EDICAO: CampoEdicao[] = [{ chave: "valor_orcado", rotulo: "Valor Orçado", tipo: "decimal" }];

export function RubricasReceitaPage() {
  const { municipioSelecionadoId } = useScope();
  const exibirAvisos = useParametro("exibir_avisos_informativos");
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [rubricas, setRubricas] = useState<RubricaReceita[]>([]);
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

  const loaId = exercicios.find((e) => e.id === exercicioId)?.loa_id ?? null;

  function recarregar() {
    if (!loaId) {
      setRubricas([]);
      return;
    }
    setCarregando(true);
    api
      .get<{ results: RubricaReceita[] }>("/rubricas-receita/", { params: { loa: loaId, page_size: 1000 } })
      .then(({ data }) => setRubricas(data.results))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    recarregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaId]);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Rubricas de Receita
      </Typography>

      {exibirAvisos && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Importado de FICHAS_RECEITAS.PDF (a LOA de receita com valores). O Valor Orçado pode ser corrigido
          manualmente pelo ícone de edição.
        </Alert>
      )}

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <Typography variant="body2">Exercício:</Typography>
        <Select size="small" value={exercicioId} onChange={(e) => setExercicioId(Number(e.target.value))}>
          {exercicios.map((ex) => (
            <MenuItem key={ex.id} value={ex.id}>
              {ex.ano}
            </MenuItem>
          ))}
        </Select>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nome</TableCell>
              <TableCell>Unidade Gestora</TableCell>
              <TableCell>Fonte de Recursos</TableCell>
              <TableCell>Tipo (STN, nível 7)</TableCell>
              <TableCell>Dedução?</TableCell>
              <TableCell align="right">Valor Orçado</TableCell>
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && rubricas.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  Nenhuma rubrica de receita cadastrada para este exercício.
                </TableCell>
              </TableRow>
            )}
            {rubricas
              .slice()
              .sort((a, b) => a.codigo.localeCompare(b.codigo))
              .map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nome}</TableCell>
                  <TableCell>{r.unidade_gestora_nome}</TableCell>
                  <TableCell>
                    {r.fonte_recursos_codigo} - {r.fonte_recursos_nome}
                  </TableCell>
                  <TableCell>{r.classificacao_tipo_codigo ?? "—"}</TableCell>
                  <TableCell>
                    {r.eh_deducao ? (
                      <Chip
                        size="small"
                        color="warning"
                        label={`Dedução de ${r.rubrica_principal_codigo ?? "—"}`}
                      />
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell align="right">{formatarMoeda(r.valor_orcado)}</TableCell>
                  <TableCell align="right">
                    <AcoesRegistroManual
                      item={r}
                      recurso="rubricas-receita"
                      campos={CAMPOS_EDICAO}
                      rotuloItem={`${r.codigo} - ${r.nome}`}
                      onSalvo={recarregar}
                    />
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
