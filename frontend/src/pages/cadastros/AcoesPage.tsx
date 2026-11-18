import { useEffect, useState } from "react";
import { Box, MenuItem, Select, Typography } from "@mui/material";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { useScope } from "../../scope/ScopeContext";
import type { Exercicio } from "../../api/types";

const TIPOS_ACAO: OpcaoCampo[] = [
  { value: "PROJETO", label: "Projeto" },
  { value: "ATIVIDADE", label: "Atividade" },
  { value: "OPERACAO_ESPECIAL", label: "Operação Especial" },
];

export function AcoesPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [opcoesPrograma, setOpcoesPrograma] = useState<OpcaoCampo[]>([]);

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

  useEffect(() => {
    if (!loaId) {
      setOpcoesPrograma([]);
      return;
    }
    api.get("/programas/", { params: { loa: loaId, page_size: 200 } }).then(({ data }) => {
      setOpcoesPrograma(
        (data.results ?? data).map((p: { id: number; codigo: string; nome: string }) => ({
          value: p.id,
          label: `${p.codigo} - ${p.nome}`,
        }))
      );
    });
  }, [loaId]);

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

      {opcoesPrograma.length > 0 ? (
        <CrudManager
          titulo="Ações"
          recurso="acoes"
          campos={[
            { chave: "programa", rotulo: "Programa", tipo: "select", opcoes: opcoesPrograma, obrigatorio: true },
            { chave: "codigo", rotulo: "Código", obrigatorio: true },
            { chave: "nome", rotulo: "Nome", obrigatorio: true },
            { chave: "tipo", rotulo: "Tipo", tipo: "select", opcoes: TIPOS_ACAO, obrigatorio: true },
            { chave: "funcao_nome", rotulo: "Função", somenteColuna: true },
            {
              chave: "desconsiderar_pnae_peae",
              rotulo: "Desconsiderar PNAE e PEAE (recursos próprios) no MDE",
              tipo: "booleano",
            },
          ]}
          dependenciasRecarregar={[opcoesPrograma.length]}
        />
      ) : (
        <Typography color="text.secondary">Cadastre ao menos um Programa para este exercício primeiro.</Typography>
      )}
    </Box>
  );
}
