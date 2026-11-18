import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { api } from "../../api/client";
import type { Exercicio, Importacao, StatusImportacao } from "../../api/types";
import { useScope } from "../../scope/ScopeContext";
import { useParametro } from "../../parametros/ParametrosContext";

// Um valor por parser/comando real do pipeline — ver
// `apps.importacao.dispatcher.MAPEAMENTO` no backend, que é a fonte de
// verdade (esta lista só precisa ficar em sincronia com ela).
const TIPOS_RELATORIO = [
  { value: "ESTRUTURA_ORGANIZACIONAL", label: "Estrutura Organizacional" },
  { value: "LOA_RELACIONAMENTO_ACOES", label: "LOA — Relacionamento das Ações" },
  { value: "LOA_DOTACOES", label: "LOA — Movimentos de Despesa Fixada (dotações)" },
  { value: "FICHAS_DESPESA", label: "Tabela de Fichas de Despesa" },
  { value: "EMPENHOS", label: "Relatório de Empenhos (mensal)" },
  { value: "FONTES_RECURSOS", label: "Fontes de Recursos" },
  { value: "FICHAS_RECEITAS", label: "Classificação Econômica da Receita (fichas)" },
  { value: "EXECUCAO_RECEITA", label: "Demonstrativo da Receita por Classificação Econômica" },
  { value: "SALDO_BALANCO", label: "Movimentos de Saldos de Balanço" },
  { value: "SALDO_CONTA_BANCARIA", label: "Relação de Saldos por Conta Bancária" },
  { value: "RESTOS_A_PAGAR", label: "Demonstrativo dos Restos a Pagar" },
  { value: "ENRIQUECIMENTO_RESTOS_A_PAGAR", label: "Saldo das Fichas de Restos a Pagar (enriquecimento)" },
  { value: "DTP", label: "RGF-Anexo 1 — Despesa Total com Pessoal" },
  { value: "MDE_MAGISTERIO_VAAT_FUNDEB", label: "RREO-Anexo 8 — MDE/Magistério/VAAT/FUNDEB" },
  { value: "ASPS", label: "RREO-Anexo XII — Ações e Serviços Públicos de Saúde" },
];

// Só este tipo precisa de Exercício (grava na LOA do exercício, não no
// município) — ver `dispatcher.py`'s `destino="loa"`. Os demais aceitam
// Exercício como metadado opcional, sem exigência.
const TIPOS_QUE_EXIGEM_EXERCICIO = new Set(["LOA_RELACIONAMENTO_ACOES"]);

const STATUS_COR: Record<StatusImportacao, "default" | "info" | "success" | "error"> = {
  PENDENTE: "default",
  PROCESSANDO: "info",
  CONCLUIDA: "success",
  ERRO: "error",
};

export function ImportacoesPage() {
  const { municipioSelecionadoId } = useScope();
  const exibirAvisos = useParametro("exibir_avisos_informativos");
  const [importacoes, setImportacoes] = useState<Importacao[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [dialogoAberto, setDialogoAberto] = useState(false);
  const [tipoRelatorio, setTipoRelatorio] = useState("ESTRUTURA_ORGANIZACIONAL");
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [processando, setProcessando] = useState<number | null>(null);

  async function carregar() {
    if (!municipioSelecionadoId) return;
    setCarregando(true);
    try {
      const { data } = await api.get("/importacoes/", {
        params: { municipio: municipioSelecionadoId, page_size: 200 },
      });
      setImportacoes(data.results ?? data);
      setErro(null);
    } catch {
      setErro("Não foi possível carregar o histórico de importações.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [municipioSelecionadoId]);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => setExercicios(data.results));
  }, [municipioSelecionadoId]);

  async function enviar() {
    if (!arquivo || !municipioSelecionadoId) return;
    setEnviando(true);
    try {
      const formData = new FormData();
      formData.append("municipio", String(municipioSelecionadoId));
      formData.append("tipo_relatorio", tipoRelatorio);
      formData.append("sistema_origem", "ASPEC");
      formData.append("arquivo", arquivo);
      if (exercicioId) formData.append("exercicio", String(exercicioId));
      const { data: novaImportacao } = await api.post("/importacoes/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDialogoAberto(false);
      setArquivo(null);
      await carregar();
      await processar(novaImportacao.id);
    } catch {
      setErro("Não foi possível enviar o arquivo.");
    } finally {
      setEnviando(false);
    }
  }

  async function processar(id: number) {
    setProcessando(id);
    try {
      await api.post(`/importacoes/${id}/processar/`);
      await carregar();
    } catch (e) {
      const detalhe =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Não foi possível processar esta importação.";
      setErro(detalhe);
      await carregar();
    } finally {
      setProcessando(null);
    }
  }

  async function excluir(item: Importacao) {
    if (!window.confirm(`Excluir o registro de importação "${item.arquivo}"?`)) return;
    try {
      await api.delete(`/importacoes/${item.id}/`);
      await carregar();
    } catch {
      setErro("Não foi possível excluir este registro.");
    }
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5">Importações</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogoAberto(true)}>
          Enviar Arquivo
        </Button>
      </Box>

      {exibirAvisos && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Enviar um arquivo aqui já roda automaticamente o parser e a importação certos para o tipo de relatório
          escolhido (sem precisar de linha de comando). Reenviar um relatório do mesmo tipo/período substitui os
          dados já importados, nunca soma — mesma regra de todo o resto do sistema. Se o processamento falhar,
          a mensagem de erro aparece na tabela abaixo; corrija o arquivo/tipo e tente novamente com o botão ▶.
        </Alert>
      )}

      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>
          {erro}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Arquivo</TableCell>
              <TableCell>Tipo de Relatório</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Linhas Importadas</TableCell>
              <TableCell>Mensagem</TableCell>
              <TableCell>Enviado por</TableCell>
              <TableCell>Data</TableCell>
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && importacoes.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  Nenhuma importação registrada.
                </TableCell>
              </TableRow>
            )}
            {importacoes.map((imp) => (
              <TableRow key={imp.id}>
                <TableCell>{imp.arquivo.split("/").pop()}</TableCell>
                <TableCell>{imp.tipo_relatorio_label}</TableCell>
                <TableCell>
                  <Chip size="small" color={STATUS_COR[imp.status]} label={imp.status_label} />
                </TableCell>
                <TableCell align="right">{imp.linhas_importadas}</TableCell>
                <TableCell sx={{ maxWidth: 320, whiteSpace: "pre-line" }}>{imp.mensagem_erro || "—"}</TableCell>
                <TableCell>{imp.usuario_nome}</TableCell>
                <TableCell>{new Date(imp.criado_em).toLocaleString("pt-BR")}</TableCell>
                <TableCell align="right">
                  <Tooltip title={imp.status === "PROCESSANDO" ? "Processando..." : "(Re)processar"}>
                    <span>
                      <IconButton
                        size="small"
                        disabled={processando === imp.id || imp.status === "PROCESSANDO"}
                        onClick={() => processar(imp.id)}
                      >
                        <PlayArrowIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                  <IconButton size="small" onClick={() => excluir(imp)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogoAberto} onClose={() => setDialogoAberto(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Enviar Arquivo para Importação</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          <TextField
            select
            label="Tipo de Relatório"
            value={tipoRelatorio}
            onChange={(e) => setTipoRelatorio(e.target.value)}
            fullWidth
          >
            {TIPOS_RELATORIO.map((t) => (
              <MenuItem key={t.value} value={t.value}>
                {t.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Exercício"
            required={TIPOS_QUE_EXIGEM_EXERCICIO.has(tipoRelatorio)}
            helperText={
              TIPOS_QUE_EXIGEM_EXERCICIO.has(tipoRelatorio)
                ? "Obrigatório para este tipo — grava na LOA do exercício selecionado."
                : "Opcional — só metadado para a maioria dos tipos."
            }
            value={exercicioId}
            onChange={(e) => setExercicioId(e.target.value ? Number(e.target.value) : "")}
            fullWidth
          >
            <MenuItem value="">Nenhum</MenuItem>
            {exercicios.map((ex) => (
              <MenuItem key={ex.id} value={ex.id}>
                Exercício {ex.ano}
              </MenuItem>
            ))}
          </TextField>
          <Button component="label" variant="outlined">
            {arquivo ? arquivo.name : "Escolher Arquivo"}
            <input
              type="file"
              hidden
              onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
            />
          </Button>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogoAberto(false)}>Cancelar</Button>
          <Button variant="contained" disabled={!arquivo || enviando} onClick={enviar}>
            Enviar e Processar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
