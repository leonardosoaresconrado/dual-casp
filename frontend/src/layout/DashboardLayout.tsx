import { useState, type ReactNode } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import {
  AppBar,
  Box,
  Collapse,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Select,
  Toolbar,
  Typography,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import GavelIcon from "@mui/icons-material/Gavel";
import BarChartIcon from "@mui/icons-material/BarChart";
import SettingsIcon from "@mui/icons-material/Settings";
import PolicyIcon from "@mui/icons-material/Policy";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import LogoutIcon from "@mui/icons-material/Logout";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useAuth } from "../auth/AuthContext";
import { useScope } from "../scope/ScopeContext";

const DRAWER_WIDTH = 300;

interface NavLink {
  type: "link";
  label: string;
  path: string;
  icon?: ReactNode;
}

interface NavGroup {
  type: "group";
  label: string;
  icon?: ReactNode;
  children: NavNode[];
  abertoPorPadrao?: boolean;
}

type NavNode = NavLink | NavGroup;

function link(label: string, path: string, icon?: ReactNode): NavLink {
  return { type: "link", label, path, icon };
}

function group(label: string, children: NavNode[], icon?: ReactNode, abertoPorPadrao?: boolean): NavGroup {
  return { type: "group", label, children, icon, abertoPorPadrao };
}

const NAV_TREE: NavNode[] = [
  group(
    "Execução Orçamentária",
    [link("Despesas", "/execucao-orcamentaria"), link("Receitas", "/receita")],
    <AccountBalanceIcon />,
    true
  ),
  group(
    "Execução Financeira",
    [
      link("Saldo de Balanço", "/financeiro/saldo-balanco"),
      link("Saldo por Conta Bancária", "/financeiro/saldo-conta"),
      link("Restos a Pagar", "/financeiro/restos-a-pagar"),
    ],
    <AccountBalanceWalletIcon />
  ),
  link("Execução Fiscal", "/execucao-fiscal", <PolicyIcon />),
  link("Obrigações (TCM-PA)", "/obrigacoes", <FactCheckIcon />),
  group(
    "Orçamento",
    [
      link("PPA", "/orcamento/ppa"),
      link("LDO", "/orcamento/ldo"),
      group("LOA", [
        link("Dados da LOA", "/cadastros/loa"),
        link("Exercícios", "/cadastros/exercicios"),
        group("Despesas", [
          link("Rubricas de Despesa", "/orcamento/loa/despesas/rubricas"),
          link("Estrutura Organizacional", "/cadastros/estrutura-organizacional"),
          link("Funções", "/cadastros/funcoes"),
          link("Subfunções", "/cadastros/subfuncoes"),
          link("Programas", "/cadastros/programas"),
          link("Ações", "/cadastros/acoes"),
          link("Categorias Econômicas", "/cadastros/categorias-economicas"),
          link("Grupos de Natureza de Despesa", "/cadastros/grupos-natureza-despesa"),
          link("Modalidades de Aplicação", "/cadastros/modalidades-aplicacao"),
          link("Elementos de Despesa", "/cadastros/elementos-despesa"),
          link("Subelementos de Despesa", "/cadastros/subelementos"),
          link("Fontes de Recursos", "/cadastros/fontes-recursos"),
        ]),
        group("Receitas", [
          link("Rubricas de Receita", "/orcamento/loa/receitas"),
          group("Classificação STN (Ementário)", [
            link("Origens", "/orcamento/loa/receitas/origens"),
            link("Espécies", "/orcamento/loa/receitas/especies"),
            link("Rubricas", "/orcamento/loa/receitas/rubricas-stn"),
            link("Alíneas", "/orcamento/loa/receitas/alineas"),
            link("Subalíneas", "/orcamento/loa/receitas/subalineas"),
            link("Tipos", "/orcamento/loa/receitas/tipos"),
          ]),
        ]),
      ]),
    ],
    <GavelIcon />
  ),
  group(
    "Relatórios",
    [
      link("Orçamento", "/relatorio-loa"),
      link("Receitas", "/relatorios/receitas"),
      link("Despesas", "/relatorio-execucao"),
      link("Financeiro", "/relatorios/financeiro"),
      link("Restos a Pagar", "/relatorios/restos-a-pagar"),
    ],
    <BarChartIcon />
  ),
  group(
    "Administração",
    [
      link("Municípios", "/admin/municipios"),
      link("Unidades Gestoras", "/admin/unidades-gestoras"),
      link("Usuários", "/admin/usuarios"),
      link("Importações", "/admin/importacoes"),
      link("Parâmetros", "/admin/parametros"),
      link("Tipos de Obrigação", "/admin/tipos-obrigacao"),
    ],
    <SettingsIcon />
  ),
];

function NavNodeView({ node, depth }: { node: NavNode; depth: number }) {
  const location = useLocation();
  const [aberto, setAberto] = useState(node.type === "group" ? !!node.abertoPorPadrao : false);
  const indent = 2 + depth * 2;

  if (node.type === "link") {
    return (
      <ListItemButton
        component={RouterLink}
        to={node.path}
        selected={location.pathname === node.path}
        sx={{ pl: indent }}
      >
        {node.icon && <ListItemIcon>{node.icon}</ListItemIcon>}
        <ListItemText primary={node.label} slotProps={depth > 0 ? { primary: { variant: "body2" } } : undefined} />
      </ListItemButton>
    );
  }

  return (
    <>
      <ListItemButton onClick={() => setAberto((v) => !v)} sx={{ pl: indent }}>
        {node.icon && <ListItemIcon>{node.icon}</ListItemIcon>}
        <ListItemText primary={node.label} slotProps={depth > 0 ? { primary: { variant: "body2" } } : undefined} />
        {aberto ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
      </ListItemButton>
      <Collapse in={aberto} timeout="auto" unmountOnExit>
        <List component="div" disablePadding>
          {node.children.map((child) => (
            <NavNodeView key={`${child.type}-${child.label}`} node={child} depth={depth + 1} />
          ))}
        </List>
      </Collapse>
    </>
  );
}

export function DashboardLayout({ children }: { children: ReactNode }) {
  const [drawerAberto, setDrawerAberto] = useState(true);
  const { usuario, logout } = useAuth();
  const { municipios, municipioSelecionadoId, setMunicipioSelecionadoId } = useScope();

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar className="no-imprimir" position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar sx={{ gap: 2 }}>
          <IconButton color="inherit" edge="start" onClick={() => setDrawerAberto((v) => !v)}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 0 }}>
            CASP
          </Typography>

          <Select
            size="small"
            value={municipioSelecionadoId ?? ""}
            onChange={(e) => setMunicipioSelecionadoId(Number(e.target.value))}
            sx={{ ml: 4, minWidth: 260, bgcolor: "background.paper", borderRadius: 1 }}
          >
            {municipios.map((m) => (
              <MenuItem key={m.id} value={m.id}>
                {m.nome}/{m.uf}
              </MenuItem>
            ))}
          </Select>

          <Box sx={{ flexGrow: 1 }} />

          <Typography variant="body2" sx={{ mr: 2 }}>
            {usuario?.nome_completo}
          </Typography>
          <IconButton color="inherit" onClick={logout} title="Sair">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        className="no-imprimir"
        variant="persistent"
        open={drawerAberto}
        sx={{
          width: drawerAberto ? DRAWER_WIDTH : 0,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <Divider />
        <List>
          {NAV_TREE.map((node) => (
            <NavNodeView key={`${node.type}-${node.label}`} node={node} depth={0} />
          ))}
        </List>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
