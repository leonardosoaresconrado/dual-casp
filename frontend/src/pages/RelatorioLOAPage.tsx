import { useEffect, useMemo, useState } from "react";
import {
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
import { api, buscarTodasPaginas } from "../api/client";
import type { Exercicio } from "../api/types";
import { useScope } from "../scope/ScopeContext";

interface RubricaDecodificada {
  id: number;
  unidade_gestora: number;
  unidade_gestora_nome: string;
  orgao_codigo: string;
  orgao_nome: string;
  unidade_orcamentaria_codigo: string;
  unidade_orcamentaria_nome: string;
  funcao_codigo: string;
  funcao_nome: string;
  subfuncao_codigo: string;
  subfuncao_nome: string;
  programa_codigo: string;
  programa_nome: string;
  acao_codigo: string;
  acao_nome: string;
  categoria_economica_codigo: string;
  categoria_economica_nome: string;
  grupo_natureza_despesa_codigo: string;
  grupo_natureza_despesa_nome: string;
  modalidade_aplicacao_codigo: string;
  modalidade_aplicacao_nome: string;
  elemento_despesa_codigo: string;
  elemento_despesa_nome: string;
  subelemento_codigo: string;
  fonte_recursos_codigo: string;
  fonte_recursos_nome: string;
  dotacao_inicial: string;
}

function formatarMoeda(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function RelatorioLOAPage() {
  const { municipioSelecionadoId } = useScope();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  const [rubricas, setRubricas] = useState<RubricaDecodificada[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [filtroUG, setFiltroUG] = useState("");
  const [filtroOrgao, setFiltroOrgao] = useState("");
  const [filtroFonte, setFiltroFonte] = useState("");

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
      setRubricas([]);
      return;
    }
    setCarregando(true);
    buscarTodasPaginas<RubricaDecodificada>("/rubricas-orcamentarias/", { loa: loaId })
      .then(setRubricas)
      .finally(() => setCarregando(false));
  }, [loaId]);

  // Opções dos 3 filtros derivadas do próprio dataset já carregado (toda a
  // LOA vem de uma vez, ver fetch acima) — mesmo padrão de "Filtrar por"
  // já usado em RelatorioExecucaoPage.tsx/RelatorioReceitaPage.tsx.
  const opcoesUG = useMemo(() => {
    const mapa = new Map<number, string>();
    for (const r of rubricas) mapa.set(r.unidade_gestora, r.unidade_gestora_nome);
    return Array.from(mapa.entries())
      .map(([id, nome]) => ({ id, nome }))
      .sort((a, b) => a.nome.localeCompare(b.nome));
  }, [rubricas]);

  const opcoesOrgao = useMemo(() => {
    const mapa = new Map<string, string>();
    for (const r of rubricas) mapa.set(r.orgao_codigo, r.orgao_nome);
    return Array.from(mapa.entries())
      .map(([codigo, nome]) => ({ codigo, nome }))
      .sort((a, b) => a.nome.localeCompare(b.nome));
  }, [rubricas]);

  // Só as fontes que realmente têm despesa na UG/Órgão já selecionados
  // (filtro em cascata) — pedido do usuário, já que mostrar fontes sem
  // nenhuma linha naquele recorte só confundia (selecionava e a tabela
  // zerava sem explicação).
  const opcoesFonte = useMemo(() => {
    const base = rubricas.filter(
      (r) => (!filtroUG || String(r.unidade_gestora) === filtroUG) && (!filtroOrgao || r.orgao_codigo === filtroOrgao)
    );
    const mapa = new Map<string, string>();
    for (const r of base) mapa.set(r.fonte_recursos_codigo, r.fonte_recursos_nome);
    return Array.from(mapa.entries())
      .map(([codigo, nome]) => ({ codigo, nome }))
      .sort((a, b) => a.nome.localeCompare(b.nome));
  }, [rubricas, filtroUG, filtroOrgao]);

  // Se a fonte selecionada deixou de existir no recorte atual (UG/Órgão
  // mudou), volta pra "Todas" em vez de ficar presa numa seleção inválida.
  useEffect(() => {
    if (filtroFonte && !opcoesFonte.some((f) => f.codigo === filtroFonte)) {
      setFiltroFonte("");
    }
  }, [opcoesFonte, filtroFonte]);

  const rubricasFiltradas = useMemo(
    () =>
      rubricas.filter(
        (r) =>
          (!filtroUG || String(r.unidade_gestora) === filtroUG) &&
          (!filtroOrgao || r.orgao_codigo === filtroOrgao) &&
          (!filtroFonte || r.fonte_recursos_codigo === filtroFonte)
      ),
    [rubricas, filtroUG, filtroOrgao, filtroFonte]
  );

  const grupos = useMemo(() => {
    const mapa = new Map<string, { chave: string; info: RubricaDecodificada; itens: RubricaDecodificada[] }>();
    for (const r of rubricasFiltradas) {
      const chave = `${r.orgao_codigo}.${r.unidade_orcamentaria_codigo}.${r.funcao_codigo}.${r.subfuncao_codigo}.${r.programa_codigo}.${r.acao_codigo}`;
      if (!mapa.has(chave)) {
        mapa.set(chave, { chave, info: r, itens: [] });
      }
      mapa.get(chave)!.itens.push(r);
    }
    return Array.from(mapa.values()).sort((a, b) => a.chave.localeCompare(b.chave));
  }, [rubricasFiltradas]);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Relatório da LOA
      </Typography>

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <Typography variant="body2">Exercício:</Typography>
        <Select size="small" value={exercicioId} onChange={(e) => setExercicioId(Number(e.target.value))}>
          {exercicios.map((ex) => (
            <MenuItem key={ex.id} value={ex.id}>
              {ex.ano}
            </MenuItem>
          ))}
        </Select>
        <Select
          size="small"
          value={filtroUG}
          onChange={(e) => setFiltroUG(e.target.value)}
          displayEmpty
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">Todas as Unidades Gestoras</MenuItem>
          {opcoesUG.map((ug) => (
            <MenuItem key={ug.id} value={String(ug.id)}>
              {ug.nome}
            </MenuItem>
          ))}
        </Select>
        <Select
          size="small"
          value={filtroOrgao}
          onChange={(e) => setFiltroOrgao(e.target.value)}
          displayEmpty
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">Todos os Órgãos</MenuItem>
          {opcoesOrgao.map((o) => (
            <MenuItem key={o.codigo} value={o.codigo}>
              {o.codigo} - {o.nome}
            </MenuItem>
          ))}
        </Select>
        <Select
          size="small"
          value={filtroFonte}
          onChange={(e) => setFiltroFonte(e.target.value)}
          displayEmpty
          sx={{ minWidth: 240 }}
        >
          <MenuItem value="">Todas as Fontes de Recursos</MenuItem>
          {opcoesFonte.map((f) => (
            <MenuItem key={f.codigo} value={f.codigo}>
              {f.codigo} - {f.nome}
            </MenuItem>
          ))}
        </Select>
        {!carregando && <Chip size="small" label={`${grupos.length} programas de trabalho`} />}
      </Box>

      {grupos.map((grupo) => {
        const i = grupo.info;
        const totalDotacao = grupo.itens.reduce((soma, item) => soma + Number(item.dotacao_inicial), 0);
        return (
          <Paper key={grupo.chave} variant="outlined" sx={{ mb: 2, p: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
              {i.orgao_codigo}
              {i.unidade_orcamentaria_codigo} - {i.unidade_orcamentaria_nome}
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 0.5,
                my: 1,
                color: "text.secondary",
                fontSize: "0.875rem",
              }}
            >
              <span>
                <strong>Unidade Gestora:</strong> {i.unidade_gestora_nome}
              </span>
              <span>
                <strong>Órgão:</strong> {i.orgao_codigo} - {i.orgao_nome}
              </span>
              <span>
                <strong>Unidade Orçamentária:</strong> {i.unidade_orcamentaria_codigo} - {i.unidade_orcamentaria_nome}
              </span>
              <span>
                <strong>Função:</strong> {i.funcao_codigo} - {i.funcao_nome}
              </span>
              <span>
                <strong>Subfunção:</strong> {i.subfuncao_codigo} - {i.subfuncao_nome}
              </span>
              <span>
                <strong>Programa:</strong> {i.programa_codigo} - {i.programa_nome}
              </span>
              <span>
                <strong>Ação:</strong> {i.acao_codigo} - {i.acao_nome}
              </span>
            </Box>

            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Categoria</TableCell>
                    <TableCell>Natureza</TableCell>
                    <TableCell>Modalidade</TableCell>
                    <TableCell>Elemento</TableCell>
                    <TableCell>Fonte</TableCell>
                    <TableCell align="right">Dotação Inicial</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.itens.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>{item.categoria_economica_codigo} - {item.categoria_economica_nome}</TableCell>
                      <TableCell>{item.grupo_natureza_despesa_codigo} - {item.grupo_natureza_despesa_nome}</TableCell>
                      <TableCell>{item.modalidade_aplicacao_codigo} - {item.modalidade_aplicacao_nome}</TableCell>
                      <TableCell>{item.elemento_despesa_codigo}.{item.subelemento_codigo} - {item.elemento_despesa_nome}</TableCell>
                      <TableCell>{item.fonte_recursos_codigo} - {item.fonte_recursos_nome}</TableCell>
                      <TableCell align="right">{formatarMoeda(item.dotacao_inicial)}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell colSpan={5} align="right">
                      <strong>Total da ação</strong>
                    </TableCell>
                    <TableCell align="right">
                      <strong>{formatarMoeda(String(totalDotacao))}</strong>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        );
      })}

      {!carregando && grupos.length === 0 && (
        <Typography color="text.secondary">Nenhuma dotação cadastrada para este exercício.</Typography>
      )}
    </Box>
  );
}
