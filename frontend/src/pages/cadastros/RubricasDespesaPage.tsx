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
  TablePagination,
  TableRow,
  Typography,
} from "@mui/material";
import { api } from "../../api/client";
import type { Exercicio, OrigemDotacao, RubricaOrcamentaria, UnidadeGestora } from "../../api/types";
import { useScope } from "../../scope/ScopeContext";
import { useParametro } from "../../parametros/ParametrosContext";
import { AcoesRegistroManual, type CampoEdicao } from "../../components/AcoesRegistroManual";

const ORIGEM_COR: Record<OrigemDotacao, "success" | "info" | "warning" | "default"> = {
  ORCAMENTO: "success",
  CREDITO_SUPLEMENTAR: "info",
  CREDITO_ESPECIAL: "warning",
  CREDITO_ADICIONAL: "default",
};

const CAMPOS_EDICAO: CampoEdicao[] = [
  { chave: "dotacao_inicial", rotulo: "Dotação Inicial", tipo: "decimal" },
  {
    chave: "origem_dotacao",
    rotulo: "Origem",
    tipo: "select",
    opcoes: [
      { value: "ORCAMENTO", label: "Orçamento (LOA)" },
      { value: "CREDITO_SUPLEMENTAR", label: "Crédito Suplementar" },
      { value: "CREDITO_ESPECIAL", label: "Crédito Especial" },
      { value: "CREDITO_ADICIONAL", label: "Crédito Adicional" },
    ],
  },
];

function formatarMoeda(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function RubricasDespesaPage() {
  const { municipioSelecionadoId } = useScope();
  const exibirAvisos = useParametro("exibir_avisos_informativos");
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [unidadesGestoras, setUnidadesGestoras] = useState<UnidadeGestora[]>([]);
  const [ugId, setUgId] = useState<number | "">("");
  const [rubricas, setRubricas] = useState<RubricaOrcamentaria[]>([]);
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

  const loaId = exercicios.find((e) => e.id === exercicioId)?.loa_id ?? null;

  function recarregar() {
    if (!loaId) {
      setRubricas([]);
      return;
    }
    setCarregando(true);
    api
      .get<{ results: RubricaOrcamentaria[] }>("/rubricas-orcamentarias/", {
        params: { loa: loaId, page_size: 2000, ...(ugId ? { unidade_gestora: ugId } : {}) },
      })
      .then(({ data }) => setRubricas(data.results))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    recarregar();
    setPagina(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaId, ugId]);

  const rubricasOrdenadas = rubricas
    .slice()
    .sort((a, b) =>
      `${a.orgao_codigo}${a.unidade_orcamentaria_codigo}`.localeCompare(
        `${b.orgao_codigo}${b.unidade_orcamentaria_codigo}`
      )
    );
  const rubricasPagina = rubricasOrdenadas.slice(
    pagina * linhasPorPagina,
    pagina * linhasPorPagina + linhasPorPagina
  );

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Rubricas de Despesa
      </Typography>

      {exibirAvisos && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Importado de LOA_DESPESAS_2026.pdf / FICHAS.PDF / empenhos (a combinação completa de órgão, classificação
          funcional/programática, classificação econômica e fonte). Dotação Inicial e Origem podem ser corrigidas
          manualmente pelo ícone de edição; a classificação em si (órgão, função, elemento etc.) não — isso se corrige
          nos cadastros individuais listados acima.
        </Alert>
      )}

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Typography variant="body2">Exercício:</Typography>
        <Select size="small" value={exercicioId} onChange={(e) => setExercicioId(Number(e.target.value))}>
          {exercicios.map((ex) => (
            <MenuItem key={ex.id} value={ex.id}>
              {ex.ano}
            </MenuItem>
          ))}
        </Select>

        <Typography variant="body2">Unidade Gestora:</Typography>
        <Select
          size="small"
          value={ugId}
          displayEmpty
          onChange={(e) => {
            const valor = e.target.value as number | "";
            setUgId(valor === "" ? "" : Number(valor));
          }}
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">Todas as Unidades Gestoras</MenuItem>
          {unidadesGestoras.map((ug) => (
            <MenuItem key={ug.id} value={ug.id}>
              {ug.nome}
            </MenuItem>
          ))}
        </Select>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Órgão / Unidade Orçamentária</TableCell>
              <TableCell>Programa / Ação</TableCell>
              <TableCell>Elemento de Despesa</TableCell>
              <TableCell>Fonte de Recursos</TableCell>
              <TableCell>Origem</TableCell>
              <TableCell align="right">Dotação Inicial</TableCell>
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && rubricas.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  Nenhuma rubrica de despesa cadastrada para este exercício.
                </TableCell>
              </TableRow>
            )}
            {rubricasPagina.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    {r.orgao_nome} / {r.unidade_orcamentaria_nome}
                  </TableCell>
                  <TableCell>
                    {r.programa_codigo} - {r.programa_nome}
                    <br />
                    {r.acao_codigo} - {r.acao_nome}
                  </TableCell>
                  <TableCell>
                    {r.elemento_despesa_codigo} - {r.elemento_despesa_nome}
                    {r.subelemento_nome ? ` / ${r.subelemento_codigo} - ${r.subelemento_nome}` : ""}
                  </TableCell>
                  <TableCell>
                    {r.fonte_recursos_codigo} - {r.fonte_recursos_nome}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" color={ORIGEM_COR[r.origem_dotacao]} label={r.origem_dotacao_label} />
                  </TableCell>
                  <TableCell align="right">{formatarMoeda(r.dotacao_inicial)}</TableCell>
                  <TableCell align="right">
                    <AcoesRegistroManual
                      item={r}
                      recurso="rubricas-orcamentarias"
                      campos={CAMPOS_EDICAO}
                      rotuloItem={`${r.elemento_despesa_nome} (${r.orgao_nome})`}
                      onSalvo={recarregar}
                    />
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={rubricasOrdenadas.length}
          page={pagina}
          onPageChange={(_, novaPagina) => setPagina(novaPagina)}
          rowsPerPage={linhasPorPagina}
          onRowsPerPageChange={(e) => {
            setLinhasPorPagina(Number(e.target.value));
            setPagina(0);
          }}
          rowsPerPageOptions={[25, 50, 100]}
          labelRowsPerPage="Linhas por página"
        />
      </TableContainer>
    </Box>
  );
}
