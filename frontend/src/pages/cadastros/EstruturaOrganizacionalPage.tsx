import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Collapse,
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
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { api } from "../../api/client";
import { useScope } from "../../scope/ScopeContext";
import { useParametro } from "../../parametros/ParametrosContext";

interface Orgao {
  id: number;
  municipio: number;
  codigo: string;
  nome: string;
  ativo: boolean;
}

interface UnidadeOrcamentaria {
  id: number;
  orgao: number;
  orgao_nome: string;
  unidade_gestora: number;
  unidade_gestora_nome: string;
  codigo: string;
  nome: string;
  ativo: boolean;
}

interface UnidadeGestora {
  id: number;
  codigo: string;
  nome: string;
  unidades_orcamentarias: UnidadeOrcamentaria[];
}

interface GrupoOrgao {
  orgaoId: number;
  orgaoNome: string;
  unidades: UnidadeOrcamentaria[];
}

type Dialogo =
  | { tipo: "orgao"; dados: { id?: number; codigo: string; nome: string; ativo: boolean } }
  | {
      tipo: "unidade";
      ugId: number;
      ugNome: string;
      orgaoFixo?: { id: number; nome: string };
      dados: { id?: number; orgao: number | ""; codigo: string; nome: string; ativo: boolean };
    };

function agruparPorOrgao(unidades: UnidadeOrcamentaria[]): GrupoOrgao[] {
  const mapa = new Map<number, GrupoOrgao>();
  for (const u of unidades) {
    if (!mapa.has(u.orgao)) {
      mapa.set(u.orgao, { orgaoId: u.orgao, orgaoNome: u.orgao_nome, unidades: [] });
    }
    mapa.get(u.orgao)!.unidades.push(u);
  }
  return Array.from(mapa.values()).sort((a, b) => a.orgaoNome.localeCompare(b.orgaoNome));
}

function LinhaUnidade({
  unidade,
  onEditar,
  onExcluir,
}: {
  unidade: UnidadeOrcamentaria;
  onEditar: () => void;
  onExcluir: () => void;
}) {
  return (
    <TableRow hover>
      <TableCell sx={{ pl: 8 }}>{unidade.codigo}</TableCell>
      <TableCell>{unidade.nome}</TableCell>
      <TableCell>{unidade.ativo ? "Sim" : "Não"}</TableCell>
      <TableCell align="right">
        <IconButton size="small" onClick={onEditar}>
          <EditIcon fontSize="small" />
        </IconButton>
        <IconButton size="small" onClick={onExcluir}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      </TableCell>
    </TableRow>
  );
}

function LinhaOrgao({
  grupo,
  ug,
  onNovaUnidade,
  onEditarUnidade,
  onExcluirUnidade,
  onEditarOrgao,
  onExcluirOrgao,
}: {
  grupo: GrupoOrgao;
  ug: UnidadeGestora;
  onNovaUnidade: () => void;
  onEditarUnidade: (u: UnidadeOrcamentaria) => void;
  onExcluirUnidade: (u: UnidadeOrcamentaria) => void;
  onEditarOrgao: () => void;
  onExcluirOrgao: () => void;
}) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox" sx={{ pl: 4 }}>
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell sx={{ fontWeight: "bold" }} colSpan={2}>
          {grupo.orgaoNome}
        </TableCell>
        <TableCell align="right">{grupo.unidades.length} unidade(s)</TableCell>
        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
          <IconButton size="small" onClick={onNovaUnidade} title={`Nova unidade orçamentária em ${ug.nome}`}>
            <AddIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={onEditarOrgao} title="Editar órgão">
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={onExcluirOrgao} title="Excluir órgão">
            <DeleteIcon fontSize="small" />
          </IconButton>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={5} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 1 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ pl: 8 }}>Código</TableCell>
                    <TableCell>Nome</TableCell>
                    <TableCell>Ativo</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {grupo.unidades
                    .slice()
                    .sort((a, b) => a.codigo.localeCompare(b.codigo))
                    .map((u) => (
                      <LinhaUnidade
                        key={u.id}
                        unidade={u}
                        onEditar={() => onEditarUnidade(u)}
                        onExcluir={() => onExcluirUnidade(u)}
                      />
                    ))}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

function LinhaUG({
  ug,
  onNovaUnidade,
  onNovaUnidadeOrgao,
  onEditarUnidade,
  onExcluirUnidade,
  onEditarOrgao,
  onExcluirOrgao,
}: {
  ug: UnidadeGestora;
  onNovaUnidade: (ug: UnidadeGestora) => void;
  onNovaUnidadeOrgao: (ug: UnidadeGestora, orgao: { id: number; nome: string }) => void;
  onEditarUnidade: (u: UnidadeOrcamentaria) => void;
  onExcluirUnidade: (u: UnidadeOrcamentaria) => void;
  onEditarOrgao: (orgaoId: number, nomeAtual: string) => void;
  onExcluirOrgao: (orgaoId: number, nome: string) => void;
}) {
  const [aberto, setAberto] = useState(false);
  const grupos = agruparPorOrgao(ug.unidades_orcamentarias);

  return (
    <>
      <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setAberto((v) => !v)}>
        <TableCell padding="checkbox">
          <IconButton size="small">
            {aberto ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </TableCell>
        <TableCell sx={{ fontWeight: "bold" }} colSpan={2}>
          {ug.nome}
        </TableCell>
        <TableCell align="right">{grupos.length} órgão(s)</TableCell>
        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
          <Button size="small" startIcon={<AddIcon />} onClick={() => onNovaUnidade(ug)}>
            Nova Unidade Orçamentária
          </Button>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={5} sx={{ py: 0, borderBottom: aberto ? undefined : "none" }}>
          <Collapse in={aberto} unmountOnExit>
            <Box sx={{ m: 1 }}>
              {grupos.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ pl: 4, py: 1 }}>
                  Nenhuma unidade orçamentária nesta Unidade Gestora ainda.
                </Typography>
              ) : (
                <Table size="small">
                  <TableBody>
                    {grupos.map((g) => (
                      <LinhaOrgao
                        key={g.orgaoId}
                        grupo={g}
                        ug={ug}
                        onNovaUnidade={() => onNovaUnidadeOrgao(ug, { id: g.orgaoId, nome: g.orgaoNome })}
                        onEditarUnidade={onEditarUnidade}
                        onExcluirUnidade={onExcluirUnidade}
                        onEditarOrgao={() => onEditarOrgao(g.orgaoId, g.orgaoNome)}
                        onExcluirOrgao={() => onExcluirOrgao(g.orgaoId, g.orgaoNome)}
                      />
                    ))}
                  </TableBody>
                </Table>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export function EstruturaOrganizacionalPage() {
  const { municipioSelecionadoId } = useScope();
  const exibirAvisos = useParametro("exibir_avisos_informativos");
  const [ugs, setUgs] = useState<UnidadeGestora[]>([]);
  const [orgaos, setOrgaos] = useState<Orgao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function carregar() {
    if (!municipioSelecionadoId) return;
    setCarregando(true);
    try {
      const [respUgs, respOrgaos] = await Promise.all([
        api.get("/unidades-gestoras/", { params: { municipio: municipioSelecionadoId, page_size: 200 } }),
        api.get("/orgaos/", { params: { municipio: municipioSelecionadoId, page_size: 500 } }),
      ]);
      setUgs(respUgs.data.results ?? respUgs.data);
      setOrgaos(respOrgaos.data.results ?? respOrgaos.data);
      setErro(null);
    } catch {
      setErro("Não foi possível carregar a estrutura organizacional.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [municipioSelecionadoId]);

  async function salvarOrgao(dados: { id?: number; codigo: string; nome: string; ativo: boolean }) {
    setSalvando(true);
    try {
      if (dados.id) {
        await api.patch(`/orgaos/${dados.id}/`, dados);
      } else {
        await api.post("/orgaos/", { ...dados, municipio: municipioSelecionadoId });
      }
      setDialogo(null);
      await carregar();
    } catch {
      setErro("Não foi possível salvar o órgão. Confira os campos obrigatórios.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluirOrgao(orgaoId: number, nome: string) {
    if (!window.confirm(`Excluir o órgão "${nome}"?`)) return;
    try {
      await api.delete(`/orgaos/${orgaoId}/`);
      await carregar();
    } catch {
      setErro("Não foi possível excluir este órgão (pode ter unidades orçamentárias vinculadas).");
    }
  }

  async function salvarUnidade(dialogoUnidade: Dialogo & { tipo: "unidade" }) {
    const { dados, ugId } = dialogoUnidade;
    if (!dados.orgao) {
      setErro("Selecione o órgão.");
      return;
    }
    setSalvando(true);
    try {
      const payload = {
        orgao: dados.orgao,
        unidade_gestora: ugId,
        codigo: dados.codigo,
        nome: dados.nome,
        ativo: dados.ativo,
      };
      if (dados.id) {
        await api.patch(`/unidades-orcamentarias/${dados.id}/`, payload);
      } else {
        await api.post("/unidades-orcamentarias/", payload);
      }
      setDialogo(null);
      await carregar();
    } catch {
      setErro("Não foi possível salvar a unidade orçamentária. Confira os campos obrigatórios.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluirUnidade(u: UnidadeOrcamentaria) {
    if (!window.confirm(`Excluir a unidade orçamentária "${u.nome}"?`)) return;
    try {
      await api.delete(`/unidades-orcamentarias/${u.id}/`);
      await carregar();
    } catch {
      setErro("Não foi possível excluir esta unidade orçamentária (pode estar em uso).");
    }
  }

  if (!municipioSelecionadoId) return null;

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5">Estrutura Organizacional</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setDialogo({ tipo: "orgao", dados: { codigo: "", nome: "", ativo: true } })}
        >
          Novo Órgão
        </Button>
      </Box>
      {exibirAvisos && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Unidade Gestora → Órgão → Unidade Orçamentária. Um órgão não pertence a uma única UG — ele pode ter
          unidades orçamentárias em UGs diferentes (ex.: Secretaria de Educação tem unidade no Fundo Municipal de
          Educação e outra no FUNDEB); por isso ele aparece sob cada UG onde já tem alguma unidade cadastrada.
        </Typography>
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
              <TableCell padding="checkbox" />
              <TableCell colSpan={2}>Unidade Gestora</TableCell>
              <TableCell align="right">Órgãos</TableCell>
              <TableCell align="right">Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && ugs.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  Nenhuma Unidade Gestora cadastrada.
                </TableCell>
              </TableRow>
            )}
            {ugs.map((ug) => (
              <LinhaUG
                key={ug.id}
                ug={ug}
                onNovaUnidade={(ug) =>
                  setDialogo({
                    tipo: "unidade",
                    ugId: ug.id,
                    ugNome: ug.nome,
                    dados: { orgao: "", codigo: "", nome: "", ativo: true },
                  })
                }
                onNovaUnidadeOrgao={(ug, orgao) =>
                  setDialogo({
                    tipo: "unidade",
                    ugId: ug.id,
                    ugNome: ug.nome,
                    orgaoFixo: orgao,
                    dados: { orgao: orgao.id, codigo: "", nome: "", ativo: true },
                  })
                }
                onEditarUnidade={(u) =>
                  setDialogo({
                    tipo: "unidade",
                    ugId: u.unidade_gestora,
                    ugNome: u.unidade_gestora_nome,
                    orgaoFixo: { id: u.orgao, nome: u.orgao_nome },
                    dados: { id: u.id, orgao: u.orgao, codigo: u.codigo, nome: u.nome, ativo: u.ativo },
                  })
                }
                onExcluirUnidade={excluirUnidade}
                onEditarOrgao={(orgaoId, nomeAtual) => {
                  const orgao = orgaos.find((o) => o.id === orgaoId);
                  setDialogo({
                    tipo: "orgao",
                    dados: orgao
                      ? { id: orgao.id, codigo: orgao.codigo, nome: orgao.nome, ativo: orgao.ativo }
                      : { id: orgaoId, codigo: "", nome: nomeAtual, ativo: true },
                  });
                }}
                onExcluirOrgao={excluirOrgao}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogo !== null} onClose={() => setDialogo(null)} maxWidth="sm" fullWidth>
        {dialogo?.tipo === "orgao" && (
          <>
            <DialogTitle>{dialogo.dados.id ? "Editar" : "Novo"} Órgão</DialogTitle>
            <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
              <TextField
                label="Código"
                required
                fullWidth
                value={dialogo.dados.codigo}
                onChange={(e) =>
                  setDialogo({ tipo: "orgao", dados: { ...dialogo.dados, codigo: e.target.value } })
                }
              />
              <TextField
                label="Nome"
                required
                fullWidth
                value={dialogo.dados.nome}
                onChange={(e) =>
                  setDialogo({ tipo: "orgao", dados: { ...dialogo.dados, nome: e.target.value } })
                }
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={dialogo.dados.ativo}
                    onChange={(e) =>
                      setDialogo({ tipo: "orgao", dados: { ...dialogo.dados, ativo: e.target.checked } })
                    }
                  />
                }
                label="Ativo"
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDialogo(null)}>Cancelar</Button>
              <Button variant="contained" disabled={salvando} onClick={() => salvarOrgao(dialogo.dados)}>
                Salvar
              </Button>
            </DialogActions>
          </>
        )}

        {dialogo?.tipo === "unidade" && (
          <>
            <DialogTitle>
              {dialogo.dados.id ? "Editar" : "Nova"} Unidade Orçamentária em {dialogo.ugNome}
            </DialogTitle>
            <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
              {dialogo.orgaoFixo ? (
                <TextField label="Órgão" value={dialogo.orgaoFixo.nome} fullWidth disabled />
              ) : (
                <TextField
                  select
                  label="Órgão"
                  required
                  fullWidth
                  value={dialogo.dados.orgao}
                  onChange={(e) =>
                    setDialogo({
                      ...dialogo,
                      dados: { ...dialogo.dados, orgao: Number(e.target.value) },
                    })
                  }
                >
                  {orgaos.map((o) => (
                    <MenuItem key={o.id} value={o.id}>
                      {o.codigo} - {o.nome}
                    </MenuItem>
                  ))}
                </TextField>
              )}
              <TextField
                label="Código"
                required
                fullWidth
                value={dialogo.dados.codigo}
                onChange={(e) => setDialogo({ ...dialogo, dados: { ...dialogo.dados, codigo: e.target.value } })}
              />
              <TextField
                label="Nome"
                required
                fullWidth
                value={dialogo.dados.nome}
                onChange={(e) => setDialogo({ ...dialogo, dados: { ...dialogo.dados, nome: e.target.value } })}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={dialogo.dados.ativo}
                    onChange={(e) =>
                      setDialogo({ ...dialogo, dados: { ...dialogo.dados, ativo: e.target.checked } })
                    }
                  />
                }
                label="Ativo"
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDialogo(null)}>Cancelar</Button>
              <Button
                variant="contained"
                disabled={salvando}
                onClick={() => salvarUnidade(dialogo as Dialogo & { tipo: "unidade" })}
              >
                Salvar
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}
