import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
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
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RefreshIcon from "@mui/icons-material/Refresh";
import DescriptionIcon from "@mui/icons-material/Description";
import { api, buscarTodasPaginas } from "../api/client";
import type { Exercicio, Obrigacao } from "../api/types";
import { useScope } from "../scope/ScopeContext";

function formatarData(iso: string | null): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR");
}

const ROTULO_SITUACAO: Record<string, string> = {
  CUMPRIDA: "Cumprida",
  ATRASADA: "Atrasada",
  PROXIMA_DO_PRAZO: "Próxima do prazo",
  PENDENTE: "Pendente",
};

const COR_SITUACAO: Record<string, "success" | "error" | "warning" | "default"> = {
  CUMPRIDA: "success",
  ATRASADA: "error",
  PROXIMA_DO_PRAZO: "warning",
  PENDENTE: "default",
};

const SITUACOES = ["PENDENTE", "PROXIMA_DO_PRAZO", "ATRASADA", "CUMPRIDA"] as const;

export function ObrigacoesPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioAno, setExercicioAno] = useState<number | "">("");
  const [obrigacoes, setObrigacoes] = useState<Obrigacao[]>([]);
  const [filtroSituacao, setFiltroSituacao] = useState<string>("TODAS");
  const [buscaCompetencia, setBuscaCompetencia] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const [selecionadosIds, setSelecionadosIds] = useState<number[]>([]);
  const [selecionada, setSelecionada] = useState<Obrigacao | null>(null);
  const [modoLote, setModoLote] = useState(false);
  const [cumprida, setCumprida] = useState("sim");
  const [dataCumprimento, setDataCumprimento] = useState("");
  const [protocolo, setProtocolo] = useState("");
  const [observacao, setObservacao] = useState("");
  const [comprovante, setComprovante] = useState<File | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        setExercicios(data.results);
        setExercicioAno(data.results[0]?.ano ?? "");
      });
  }, [municipioSelecionadoId]);

  async function carregar() {
    if (!municipioSelecionadoId) return;
    setCarregando(true);
    try {
      await api.post("/obrigacoes/gerar/", {}, { params: { municipio: municipioSelecionadoId } });
      const params: Record<string, unknown> = { municipio: municipioSelecionadoId };
      if (exercicioAno) params.exercicio = exercicioAno;
      setObrigacoes(await buscarTodasPaginas<Obrigacao>("/obrigacoes/", params));
      setErro(null);
    } catch {
      setErro("Não foi possível carregar as obrigações.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [municipioSelecionadoId, exercicioAno]);

  const contagens = useMemo(() => {
    const c: Record<string, number> = { PENDENTE: 0, PROXIMA_DO_PRAZO: 0, ATRASADA: 0, CUMPRIDA: 0 };
    for (const o of obrigacoes) c[o.situacao] = (c[o.situacao] ?? 0) + 1;
    return c;
  }, [obrigacoes]);

  const listaFiltrada = useMemo(() => {
    let lista = filtroSituacao === "TODAS" ? obrigacoes : obrigacoes.filter((o) => o.situacao === filtroSituacao);
    const busca = buscaCompetencia.trim().toLowerCase();
    if (busca) {
      lista = lista.filter((o) => o.rotulo_competencia.toLowerCase().includes(busca));
    }
    return lista;
  }, [obrigacoes, filtroSituacao, buscaCompetencia]);

  const pendentesVisiveis = listaFiltrada.filter((o) => o.status === "PENDENTE");
  const todosVisiveisSelecionados =
    pendentesVisiveis.length > 0 && pendentesVisiveis.every((o) => selecionadosIds.includes(o.id));

  function alternarSelecao(id: number) {
    setSelecionadosIds((atual) => (atual.includes(id) ? atual.filter((x) => x !== id) : [...atual, id]));
  }

  function alternarSelecionarTodosVisiveis() {
    if (todosVisiveisSelecionados) {
      const idsVisiveis = new Set(pendentesVisiveis.map((o) => o.id));
      setSelecionadosIds((atual) => atual.filter((id) => !idsVisiveis.has(id)));
    } else {
      setSelecionadosIds((atual) => Array.from(new Set([...atual, ...pendentesVisiveis.map((o) => o.id)])));
    }
  }

  function abrirConfirmacao(o: Obrigacao) {
    setSelecionada(o);
    setModoLote(false);
    setCumprida("sim");
    setDataCumprimento(new Date().toISOString().slice(0, 10));
    setProtocolo("");
    setObservacao("");
    setComprovante(null);
  }

  function abrirConfirmacaoLote() {
    setSelecionada(null);
    setModoLote(true);
    setCumprida("sim");
    setDataCumprimento(new Date().toISOString().slice(0, 10));
    setProtocolo("");
    setObservacao("");
    setComprovante(null);
  }

  async function salvarConfirmacao() {
    if (!selecionada && !modoLote) return;
    setSalvando(true);
    try {
      if (modoLote) {
        await api.post("/obrigacoes/confirmar-lote/", {
          cumprida: cumprida === "sim",
          data_cumprimento: cumprida === "sim" ? dataCumprimento : undefined,
          protocolo,
          observacao,
          ids: selecionadosIds,
        });
        setSelecionadosIds([]);
      } else if (selecionada) {
        // Multipart apenas quando há um comprovante anexado (o recibo que o
        // usuário salvou manualmente depois de resolver o captcha) — nunca
        // baixado automaticamente de nenhum sistema do TCM-PA.
        if (comprovante) {
          const formData = new FormData();
          formData.append("cumprida", String(cumprida === "sim"));
          if (cumprida === "sim") formData.append("data_cumprimento", dataCumprimento);
          formData.append("protocolo", protocolo);
          formData.append("observacao", observacao);
          formData.append("comprovante", comprovante);
          await api.post(`/obrigacoes/${selecionada.id}/confirmar/`, formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
        } else {
          await api.post(`/obrigacoes/${selecionada.id}/confirmar/`, {
            cumprida: cumprida === "sim",
            data_cumprimento: cumprida === "sim" ? dataCumprimento : undefined,
            protocolo,
            observacao,
          });
        }
      }
      setSelecionada(null);
      setModoLote(false);
      await carregar();
    } catch {
      setErro("Não foi possível registrar a verificação.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5">Controle de Obrigações — TCM-PA</Typography>
        <Button startIcon={<RefreshIcon />} onClick={carregar} disabled={carregando}>
          Atualizar
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        As consultas do Portal NEC do TCM-PA exigem resolução manual de CAPTCHA — clique em "Verificar agora" para
        abrir o portal numa nova aba, confira o resultado e confirme aqui.
      </Alert>

      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErro(null)}>
          {erro}
        </Alert>
      )}

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <Select
          size="small"
          value={exercicioAno}
          onChange={(e) => setExercicioAno(Number(e.target.value))}
          displayEmpty
          sx={{ minWidth: 160 }}
        >
          {exercicios.length === 0 && <MenuItem value="">Sem exercícios</MenuItem>}
          {exercicios.map((ex) => (
            <MenuItem key={ex.id} value={ex.ano}>
              Exercício {ex.ano}
            </MenuItem>
          ))}
        </Select>
        <TextField
          size="small"
          label="Buscar competência"
          placeholder='ex. "Janeiro" mostra tudo que vence nessa competência'
          value={buscaCompetencia}
          onChange={(e) => setBuscaCompetencia(e.target.value)}
          sx={{ minWidth: 280 }}
        />
        {selecionadosIds.length > 0 && (
          <Button variant="contained" startIcon={<CheckCircleIcon />} onClick={abrirConfirmacaoLote}>
            Confirmar selecionadas ({selecionadosIds.length})
          </Button>
        )}
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        {SITUACOES.map((sit) => (
          <Paper
            key={sit}
            variant="outlined"
            sx={{ p: 2, minWidth: 180, flex: 1, cursor: "pointer", borderColor: filtroSituacao === sit ? "primary.main" : undefined }}
            onClick={() => setFiltroSituacao(filtroSituacao === sit ? "TODAS" : sit)}
          >
            <Typography variant="body2" color="text.secondary">
              {ROTULO_SITUACAO[sit]}
            </Typography>
            <Typography variant="h5" color={`${COR_SITUACAO[sit]}.main`}>
              {contagens[sit] ?? 0}
            </Typography>
          </Paper>
        ))}
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  size="small"
                  checked={todosVisiveisSelecionados}
                  indeterminate={!todosVisiveisSelecionados && selecionadosIds.length > 0}
                  disabled={pendentesVisiveis.length === 0}
                  onChange={alternarSelecionarTodosVisiveis}
                />
              </TableCell>
              <TableCell>Tipo de Obrigação</TableCell>
              <TableCell>Município/UG</TableCell>
              <TableCell>Competência</TableCell>
              <TableCell>Prazo</TableCell>
              <TableCell>Situação</TableCell>
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && listaFiltrada.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  Nenhuma obrigação encontrada.
                </TableCell>
              </TableRow>
            )}
            {listaFiltrada.map((o) => (
              <TableRow key={o.id} selected={selecionadosIds.includes(o.id)}>
                <TableCell padding="checkbox">
                  {o.status === "PENDENTE" && (
                    <Checkbox size="small" checked={selecionadosIds.includes(o.id)} onChange={() => alternarSelecao(o.id)} />
                  )}
                </TableCell>
                <TableCell>{o.tipo_obrigacao_nome}</TableCell>
                <TableCell>{o.unidade_gestora_nome ?? o.municipio_nome}</TableCell>
                <TableCell>{o.rotulo_competencia}</TableCell>
                <TableCell>{formatarData(o.prazo_limite)}</TableCell>
                <TableCell>
                  <Chip size="small" label={ROTULO_SITUACAO[o.situacao]} color={COR_SITUACAO[o.situacao]} />
                </TableCell>
                <TableCell align="right">
                  {o.url_consulta && (
                    <Button
                      size="small"
                      startIcon={<OpenInNewIcon />}
                      sx={{ mr: 1 }}
                      component="a"
                      href={o.url_consulta}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Verificar agora
                    </Button>
                  )}
                  {o.status === "PENDENTE" && (
                    <Button size="small" variant="outlined" startIcon={<CheckCircleIcon />} onClick={() => abrirConfirmacao(o)}>
                      Confirmar
                    </Button>
                  )}
                  {o.comprovante && (
                    <Button
                      size="small"
                      startIcon={<DescriptionIcon />}
                      sx={{ ml: 1 }}
                      component="a"
                      href={o.comprovante}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Comprovante
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog
        open={!!selecionada || modoLote}
        onClose={() => {
          setSelecionada(null);
          setModoLote(false);
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {modoLote
            ? `Confirmar verificação em lote (${selecionadosIds.length} selecionadas)`
            : `Confirmar verificação — ${selecionada?.tipo_obrigacao_nome}`}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {modoLote
              ? "A mesma data/protocolo/observação será aplicada a todas as obrigações selecionadas — útil para importar um histórico já entregue antes deste sistema existir."
              : selecionada?.rotulo_competencia}
          </Typography>
          <RadioGroup row value={cumprida} onChange={(e) => setCumprida(e.target.value)}>
            <FormControlLabel value="sim" control={<Radio />} label="Cumprida" />
            <FormControlLabel value="nao" control={<Radio />} label="Não cumprida" />
          </RadioGroup>
          {cumprida === "sim" && (
            <TextField
              label="Data do cumprimento"
              type="date"
              value={dataCumprimento}
              onChange={(e) => setDataCumprimento(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              fullWidth
            />
          )}
          <TextField label="Protocolo" value={protocolo} onChange={(e) => setProtocolo(e.target.value)} fullWidth />
          <TextField
            label="Observação"
            multiline
            minRows={2}
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            fullWidth
          />
          {!modoLote && (
            <Button component="label" variant="outlined" startIcon={<DescriptionIcon />}>
              {comprovante ? comprovante.name : "Anexar comprovante/recibo (PDF ou imagem)"}
              <input
                type="file"
                hidden
                accept="application/pdf,image/*"
                onChange={(e) => setComprovante(e.target.files?.[0] ?? null)}
              />
            </Button>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setSelecionada(null);
              setModoLote(false);
            }}
          >
            Cancelar
          </Button>
          <Button variant="contained" disabled={salvando} onClick={salvarConfirmacao}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
