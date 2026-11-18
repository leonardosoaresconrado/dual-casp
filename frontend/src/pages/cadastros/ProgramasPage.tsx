import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager } from "../../components/CrudManager";
import { useScope } from "../../scope/ScopeContext";
import type { Exercicio } from "../../api/types";
import { Box, MenuItem, Select, Typography } from "@mui/material";

export function ProgramasPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");

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

  return (
    <Box>
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

      {loaId ? (
        <CrudManager
          titulo="Programas"
          recurso="programas"
          campos={[
            { chave: "codigo", rotulo: "Código", obrigatorio: true },
            { chave: "nome", rotulo: "Nome", obrigatorio: true },
            { chave: "objetivo", rotulo: "Objetivo", tipo: "textarea" },
          ]}
          parametrosExtras={{ loa: loaId }}
          valoresPadrao={{ loa: loaId }}
        />
      ) : (
        <Typography color="text.secondary">Selecione um exercício com LOA cadastrada.</Typography>
      )}
    </Box>
  );
}
