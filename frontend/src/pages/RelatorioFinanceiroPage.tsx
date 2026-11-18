import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControlLabel,
  MenuItem,
  Paper,
  Select,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useTheme,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlineOutlined";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import { useNavigate } from "react-router-dom";
import { api, buscarTodasPaginas, buscarUltimoMesComMovimento } from "../api/client";
import type {
  Exercicio,
  LancamentoExecucaoOrcamentaria,
  LancamentoExecucaoReceita,
  RestoAPagar,
  SaldoBalancoConta,
} from "../api/types";
import { useScope } from "../scope/ScopeContext";

const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

function formatarMoeda(valor: number): string {
  // Resíduo de ponto flutuante (ex.: 758898.82 - 758898.82 - 0 vira
  // -0.0000000001) aparece como "-R$ 0,00" sem isto — cosmético, não um erro de cálculo.
  const normalizado = Math.abs(valor) < 0.005 ? 0 : valor;
  return normalizado.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// D (Devedor) soma positivo, C (Credor) soma negativo — mesma convenção usada em SaldoBalancoPage.
function valorComSinal(valor: string, natureza: string): number {
  const n = Number(valor);
  return natureza === "C" ? -n : n;
}

// Replica a planilha-modelo "Apuração de Disponibilidade por Fonte" linha a
// linha: cada coluna com o MESMO nome e a MESMA fórmula da aba "Analise da
// Disponibilidade" daquele arquivo (F..X lá = os campos abaixo). Duas
// diferenças por limitação real dos dados de origem, não por escolha:
// (1) lá "Saldo Final - RPNP/RP" vinha pronto (fonte externa não vista) e
// "Pagamentos" era um RESÍDUO (Inicial − Finais − Cancelamentos) que só
// funciona porque os Finais lá eram exatos. Aqui o relatório ASPEC não diz
// a qual "balde" um cancelamento pertence, então "Saldo Final RPNP/RP" só
// dá para ESTIMAR linha a linha (rpnpRestante = inscrição não processada −
// liquidação; rpRestante = inscrição processada + liquidação − RPP pago) —
// usar esse resíduo como estimativa já produziu "Pagamentos" negativo numa
// fonte durante o desenvolvimento (a estimativa de Final ficou maior que o
// Inicial). Por isso aqui a ordem se inverte: "Pagamentos" vem direto do
// total pago já validado (RPP pago + RPNP pago, o mesmo da página Restos a
// Pagar), e "Saldo de Restos a Pagar" é o resíduo (Inicial − Cancelamentos
// − Pagamentos) — right; "Saldo Final RPNP"/"Saldo Final RP" continuam
// mostrados (estimativa, não usada em nenhuma outra conta) só para manter
// a mesma forma visual da planilha-modelo.
// (2) "Inscrição de Restos" (R, S) e todo o grupo "Execução do Exercício"
// (N..Q) refletem só o que já ocorreu até o mês selecionado, já que 2026
// ainda não fechou — na planilha-modelo (exercício já encerrado) são os
// valores finais do ano inteiro.
interface GrupoDisponibilidade {
  codigo: string;
  nome: string;
  disponibilidadeCaixaBrutaAnterior: number;
  saldoInicialRestos: number;
  saldoFinalRPNPEstimado: number;
  saldoFinalRPEstimado: number;
  cancelamentos: number;
  pagamentosRestos: number;
  receitas: number;
  empenhos: number;
  liquidacoes: number;
  pagamentosEmpenhos: number;
}

// Agrupa por CÓDIGO da fonte — `FonteRecursos` é um catálogo nacional,
// único por código desde 2026-11-12 (ver CLAUDE.md, "FonteRecursos was
// wrongly UG-scoped"). Antes dessa correção o código variava por UG e só
// o nome servia de chave estável; agrupar por nome ficou ERRADO depois do
// fix, porque "do exercício" (código iniciado em 1) e "superávit
// financeiro de exercícios anteriores" (iniciado em 2) são fontes
// DIFERENTES que description-wise têm o mesmo nome (ex.: "Transferências
// do FUNDEB - Impostos 70%" existe como 15401070 e como 25401070) — bug
// real encontrado pelo usuário: receita de 15401070 aparecia misturada
// na linha de 25401070 (que não deveria ter receita nenhuma, só
// aplicação de superávit).
function montarDisponibilidades(
  saldosAbertura: SaldoBalancoConta[],
  restosAPagarTodos: RestoAPagar[],
  lancamentosReceita: LancamentoExecucaoReceita[],
  lancamentosDespesa: LancamentoExecucaoOrcamentaria[],
  mes: number
): GrupoDisponibilidade[] {
  const mapa = new Map<string, GrupoDisponibilidade>();

  function grupo(codigo: string, nome: string): GrupoDisponibilidade {
    if (!mapa.has(codigo)) {
      mapa.set(codigo, {
        codigo, nome, disponibilidadeCaixaBrutaAnterior: 0, saldoInicialRestos: 0,
        saldoFinalRPNPEstimado: 0, saldoFinalRPEstimado: 0, cancelamentos: 0, pagamentosRestos: 0,
        receitas: 0, empenhos: 0, liquidacoes: 0, pagamentosEmpenhos: 0,
      });
    }
    return mapa.get(codigo)!;
  }

  // F — Disponibilidade de Caixa Bruta do exercício anterior.
  for (const c of saldosAbertura) {
    for (const f of c.fontes) {
      grupo(f.fonte_recursos_codigo, f.fonte_recursos_nome).disponibilidadeCaixaBrutaAnterior +=
        valorComSinal(f.valor, f.natureza);
    }
  }

  // G — Saldo Inicial de Restos a Pagar: fixo, sempre o mês 1 (a inscrição
  // original não muda mês a mês — ver docstring de RestoAPagar).
  for (const r of restosAPagarTodos) {
    if (r.mes_referencia !== 1) continue;
    grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome).saldoInicialRestos +=
      Number(r.inscricao_processada) + Number(r.inscricao_nao_processada) + Number(r.reinscricao);
  }

  // H, I (estimativa de exibição), J, K — situação dos restos a pagar de
  // exercícios anteriores NO mês selecionado. Pagamentos (K) vem do total
  // pago já validado, não do resíduo H+I — ver nota acima.
  for (const r of restosAPagarTodos) {
    if (r.mes_referencia !== mes) continue;
    const g = grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome);
    const rpnpRestante = Math.max(0, Number(r.inscricao_nao_processada) - Number(r.liquidacao));
    const rpRestante = Math.max(
      0,
      Number(r.inscricao_processada) + Number(r.liquidacao) - Number(r.rpp_pago)
    );
    g.saldoFinalRPNPEstimado += rpnpRestante;
    g.saldoFinalRPEstimado += rpRestante;
    g.cancelamentos += Number(r.cancelamento);
    g.pagamentosRestos += Number(r.rpp_pago) + Number(r.rpnp_pago);
  }

  // N — Receitas arrecadadas no exercício corrente, acumulado até o mês.
  for (const l of lancamentosReceita) {
    if (l.mes_referencia > mes) continue;
    const r = l.rubrica_detalhe;
    grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome).receitas += Number(l.valor_liquido_no_mes);
  }

  // O, P, Q — Empenhos, Liquidações e Pagamentos da despesa do exercício corrente.
  for (const l of lancamentosDespesa) {
    const r = l.rubrica_detalhe;
    const g = grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome);
    g.empenhos += Number(l.empenhado_acumulado);
    g.liquidacoes += Number(l.liquidado_acumulado);
    g.pagamentosEmpenhos += Number(l.pago_acumulado);
  }

  return Array.from(mapa.values()).sort(
    (a, b) =>
      b.disponibilidadeCaixaBrutaAnterior + b.receitas - (a.disponibilidadeCaixaBrutaAnterior + a.receitas)
  );
}

interface Derivados {
  saldoRestosFinal: number;
  inscricaoRPNP: number;
  inscricaoRP: number;
  ingressos: number;
  dispendios: number;
  disponibilidadeCaixaBruta: number;
  disponibilidadeLiquida: number;
}

function derivar(g: GrupoDisponibilidade): Derivados {
  // L — resíduo: Inicial menos o que foi cancelado menos o que foi
  // efetivamente pago (validado) é o que ainda resta a pagar.
  const saldoRestosFinal = g.saldoInicialRestos - g.cancelamentos - g.pagamentosRestos;
  const inscricaoRPNP = g.empenhos - g.liquidacoes; // R
  const inscricaoRP = g.liquidacoes - g.pagamentosEmpenhos; // S
  const ingressos = g.disponibilidadeCaixaBrutaAnterior + g.receitas; // U
  const dispendios = g.pagamentosRestos + g.pagamentosEmpenhos; // V
  const disponibilidadeCaixaBruta = ingressos - dispendios; // W
  const disponibilidadeLiquida = disponibilidadeCaixaBruta - (inscricaoRPNP + inscricaoRP) - saldoRestosFinal; // X
  return { saldoRestosFinal, inscricaoRPNP, inscricaoRP, ingressos, dispendios, disponibilidadeCaixaBruta, disponibilidadeLiquida };
}

// --- formatação/interação da tabela ------------------------------------------

type Bloco = "saldos" | "execucao" | "resultado";

// Altura fixa da 1ª linha do cabeçalho (em px) — a tabela tem cabeçalho de 2
// linhas (bloco + coluna), e `stickyHeader` do MUI só gruda tudo em `top: 0`
// certo para cabeçalho de 1 linha só. Forçando essa altura nas células da
// 1ª linha e usando-a como `top` na 2ª, as duas linhas grudam empilhadas
// (2ª logo abaixo da 1ª) em vez de uma cobrir a outra.
const ALTURA_LINHA_CABECALHO = 37;

const ROTULO_BLOCO: Record<Bloco, string> = {
  saldos: "Saldos de Exercícios Anteriores",
  execucao: "Execução Orçamentária e Financeira do Exercício",
  resultado: "Resultado",
};

interface ColunaDisponibilidade {
  chave: string;
  rotulo: string;
  bloco: Bloco;
  valor: (g: GrupoDisponibilidade) => number;
}

function construirColunas(anoAnterior: number): ColunaDisponibilidade[] {
  return [
    {
      chave: "disponibilidadeCaixaBrutaAnterior",
      rotulo: `Disponibilidade de Caixa Bruta em 31/12/${anoAnterior}`,
      bloco: "saldos",
      valor: (g) => g.disponibilidadeCaixaBrutaAnterior,
    },
    { chave: "saldoInicialRestos", rotulo: "Saldo Inicial de Restos a Pagar", bloco: "saldos", valor: (g) => g.saldoInicialRestos },
    { chave: "saldoFinalRPNPEstimado", rotulo: "Saldo Final - RPNP (estimado)", bloco: "saldos", valor: (g) => g.saldoFinalRPNPEstimado },
    { chave: "saldoFinalRPEstimado", rotulo: "Saldo Final - RP (estimado)", bloco: "saldos", valor: (g) => g.saldoFinalRPEstimado },
    { chave: "cancelamentos", rotulo: "Cancelamentos", bloco: "saldos", valor: (g) => g.cancelamentos },
    { chave: "pagamentosRestos", rotulo: "Pagamentos", bloco: "saldos", valor: (g) => g.pagamentosRestos },
    { chave: "saldoRestosFinal", rotulo: "Saldo de Restos a Pagar", bloco: "saldos", valor: (g) => derivar(g).saldoRestosFinal },
    { chave: "receitas", rotulo: "Receitas", bloco: "execucao", valor: (g) => g.receitas },
    { chave: "empenhos", rotulo: "Empenhos", bloco: "execucao", valor: (g) => g.empenhos },
    { chave: "liquidacoes", rotulo: "Liquidações", bloco: "execucao", valor: (g) => g.liquidacoes },
    { chave: "pagamentosEmpenhos", rotulo: "Pagamentos", bloco: "execucao", valor: (g) => g.pagamentosEmpenhos },
    { chave: "inscricaoRPNP", rotulo: "Inscrição RP Não Processados", bloco: "execucao", valor: (g) => derivar(g).inscricaoRPNP },
    { chave: "inscricaoRP", rotulo: "Inscrição RP Processados", bloco: "execucao", valor: (g) => derivar(g).inscricaoRP },
    { chave: "ingressos", rotulo: "Ingressos", bloco: "resultado", valor: (g) => derivar(g).ingressos },
    { chave: "dispendios", rotulo: "Dispêndios", bloco: "resultado", valor: (g) => derivar(g).dispendios },
    { chave: "disponibilidadeCaixaBruta", rotulo: "Disponibilidade de Caixa Bruta", bloco: "resultado", valor: (g) => derivar(g).disponibilidadeCaixaBruta },
    { chave: "disponibilidadeLiquida", rotulo: "Disponibilidade Líquida", bloco: "resultado", valor: (g) => derivar(g).disponibilidadeLiquida },
  ];
}

interface Ordenacao {
  coluna: string;
  direcao: "asc" | "desc";
}

function valorOrdenacao(g: GrupoDisponibilidade, coluna: string, colunas: ColunaDisponibilidade[]): number | string {
  if (coluna === "nome") return g.nome;
  if (coluna === "codigo") return g.codigo;
  return colunas.find((c) => c.chave === coluna)?.valor(g) ?? 0;
}

interface Selecao {
  fonte: string;
  coluna: string;
}

export function RelatorioFinanceiroPage() {
  const navigate = useNavigate();
  const { municipioSelecionadoId } = useScope();
  const theme = useTheme();
  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  // 0 = ainda não sabemos qual é o último mês com movimento (ver efeito
  // abaixo) — nunca mostrado no Select, só evita buscar com o mês errado.
  const [mes, setMes] = useState<number>(0);
  const [saldosAbertura, setSaldosAbertura] = useState<SaldoBalancoConta[]>([]);
  const [lancamentosReceita, setLancamentosReceita] = useState<LancamentoExecucaoReceita[]>([]);
  const [lancamentosDespesa, setLancamentosDespesa] = useState<LancamentoExecucaoOrcamentaria[]>([]);
  const [restosAPagar, setRestosAPagar] = useState<RestoAPagar[]>([]);
  const [carregando, setCarregando] = useState(false);

  const [busca, setBusca] = useState("");
  const [somenteNegativas, setSomenteNegativas] = useState(false);
  const [somenteSuperavit, setSomenteSuperavit] = useState(false);
  const [blocosVisiveis, setBlocosVisiveis] = useState<Record<Bloco, boolean>>({
    saldos: true, execucao: true, resultado: true,
  });
  const [ordenacao, setOrdenacao] = useState<Ordenacao>({ coluna: "__padrao__", direcao: "desc" });
  const [selecao, setSelecao] = useState<Selecao | null>(null);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        setExercicios(data.results);
        setExercicioId(data.results[0]?.id ?? "");
      });
    buscarTodasPaginas<SaldoBalancoConta>("/saldo-balanco/", {}).then((todas) => {
      // saldo de abertura = a foto mais antiga disponível (início do exercício), não a mais recente.
      // Não dá pra filtrar isso no backend sem já saber a data — precisa ver
      // todas as fotos pelo menos uma vez para descobrir qual é a mais
      // antiga. Dataset pequeno hoje (só uma foto por UG), reavaliar se
      // crescer.
      const dataAbertura = todas.map((c) => c.data_referencia).sort()[0];
      setSaldosAbertura(todas.filter((c) => c.data_referencia === dataAbertura));
    });
  }, [municipioSelecionadoId]);

  const exercicioSelecionado = useMemo(
    () => exercicios.find((e) => e.id === exercicioId) ?? null,
    [exercicios, exercicioId]
  );

  // Seleciona automaticamente o último mês com empenho ao trocar de
  // exercício — nunca o mês corrente do calendário.
  useEffect(() => {
    if (!exercicioSelecionado?.loa_id) return;
    let cancelado = false;
    buscarUltimoMesComMovimento(exercicioSelecionado.loa_id).then((ultimoMes) => {
      if (cancelado) return;
      setMes(ultimoMes ?? new Date().getMonth() + 1);
    });
    return () => {
      cancelado = true;
    };
  }, [exercicioSelecionado]);

  useEffect(() => {
    if (!exercicioSelecionado?.loa_id || !mes) {
      setLancamentosReceita([]);
      return;
    }
    const loaId = exercicioSelecionado.loa_id;
    // Troca rápida de mês pode deixar uma busca antiga resolver DEPOIS da
    // mais nova (o mês com mais linhas demora mais) e sobrescrever o
    // estado com dados de um mês que não é mais o selecionado — guarda
    // de cancelamento evita isso.
    let cancelado = false;
    setCarregando(true);
    // Restos a Pagar só é usado em dois meses fixos (ver montarDisponibilidades):
    // mes_referencia=1 (saldo inicial, nunca muda) e o mês selecionado — pedir
    // só esses dois ao backend em vez do dataset inteiro, igual já fazemos
    // com mes_referencia_ate em execução de receita.
    Promise.all([
      buscarTodasPaginas<LancamentoExecucaoReceita>("/execucao-receita/", { loa: loaId, mes_referencia_ate: mes }),
      buscarTodasPaginas<LancamentoExecucaoOrcamentaria>("/execucao-orcamentaria/", { loa: loaId, mes_referencia: mes }),
      buscarTodasPaginas<RestoAPagar>("/restos-a-pagar/", { mes_referencia: 1 }),
      mes === 1
        ? Promise.resolve<RestoAPagar[]>([])
        : buscarTodasPaginas<RestoAPagar>("/restos-a-pagar/", { mes_referencia: mes }),
    ])
      .then(([receita, despesa, restosMes1, restosMesAtual]) => {
        if (cancelado) return;
        setLancamentosReceita(receita);
        setLancamentosDespesa(despesa);
        setRestosAPagar([...restosMes1, ...restosMesAtual]);
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [exercicioSelecionado, mes]);

  const grupos = useMemo(
    () => montarDisponibilidades(saldosAbertura, restosAPagar, lancamentosReceita, lancamentosDespesa, mes),
    [saldosAbertura, restosAPagar, lancamentosReceita, lancamentosDespesa, mes]
  );

  const anoExercicio = exercicioSelecionado?.ano ?? new Date().getFullYear();
  const anoAnterior = anoExercicio - 1;

  const colunas = useMemo(() => construirColunas(anoAnterior), [anoAnterior]);
  const colunasVisiveis = useMemo(() => colunas.filter((c) => blocosVisiveis[c.bloco]), [colunas, blocosVisiveis]);

  const gruposFiltrados = useMemo(() => {
    let lista = grupos;
    const alvo = busca.trim().toLowerCase();
    if (alvo) {
      lista = lista.filter((g) => g.nome.toLowerCase().includes(alvo) || g.codigo.toLowerCase().includes(alvo));
    }
    if (somenteNegativas) {
      lista = lista.filter((g) => derivar(g).disponibilidadeLiquida < 0);
    }
    if (somenteSuperavit) {
      // 1º dígito do código: "1" = Recursos do Exercício, "2" = Superávit
      // Financeiro de Exercícios Anteriores — mesma convenção de
      // FonteRecursos.natureza no backend (ver CLAUDE.md).
      lista = lista.filter((g) => g.codigo.startsWith("2"));
    }
    return lista;
  }, [grupos, busca, somenteNegativas, somenteSuperavit]);

  const gruposOrdenados = useMemo(() => {
    const copia = [...gruposFiltrados];
    if (ordenacao.coluna === "__padrao__") {
      copia.sort((a, b) => b.disponibilidadeCaixaBrutaAnterior + b.receitas - (a.disponibilidadeCaixaBrutaAnterior + a.receitas));
      return copia;
    }
    copia.sort((a, b) => {
      const va = valorOrdenacao(a, ordenacao.coluna, colunas);
      const vb = valorOrdenacao(b, ordenacao.coluna, colunas);
      const cmp = typeof va === "string" ? va.localeCompare(vb as string) : (va as number) - (vb as number);
      return ordenacao.direcao === "asc" ? cmp : -cmp;
    });
    return copia;
  }, [gruposFiltrados, ordenacao, colunas]);

  const qtdNegativas = useMemo(() => grupos.filter((g) => derivar(g).disponibilidadeLiquida < 0).length, [grupos]);

  function alternarOrdenacao(coluna: string) {
    setOrdenacao((o) => (o.coluna === coluna ? { coluna, direcao: o.direcao === "asc" ? "desc" : "asc" } : { coluna, direcao: "desc" }));
  }

  function alternarSelecao(fonte: string, coluna: string) {
    setSelecao((s) => (s && s.fonte === fonte && s.coluna === coluna ? null : { fonte, coluna }));
  }

  function corCelula(g: GrupoDisponibilidade, coluna: string): string | undefined {
    const linhaAtiva = selecao?.fonte === g.codigo;
    const colunaAtiva = selecao?.coluna === coluna;
    if (linhaAtiva && colunaAtiva) return alpha(theme.palette.info.main, 0.22);
    if (colunaAtiva) return alpha(theme.palette.info.main, 0.12);
    if (linhaAtiva) return theme.palette.action.selected;
    if (derivar(g).disponibilidadeLiquida < 0) return alpha(theme.palette.error.main, 0.06);
    return undefined;
  }

  // Cores sólidas (não alpha sobre fundo transparente) — necessário para o
  // cabeçalho "grudar" (stickyHeader) sem deixar as linhas da tabela
  // aparecerem por trás enquanto rolam, o que um bgcolor com transparência
  // deixaria vazar. Só a variante clara — o tema nunca liga modo escuro
  // (ver CLAUDE.md), a branch "dark" era código morto.
  const corCabecalhoBloco: Record<Bloco, string> = { saldos: "#f2f2f2", execucao: "#e8e8e8", resultado: "#dddddd" };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Apuração da Disponibilidade por Fonte
      </Typography>

      {qtdNegativas > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {qtdNegativas} fonte{qtdNegativas > 1 ? "s" : ""} com disponibilidade líquida negativa neste mês.
        </Alert>
      )}

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Select
            size="small"
            value={exercicioId}
            onChange={(e) => setExercicioId(Number(e.target.value))}
            displayEmpty
            sx={{ minWidth: 160 }}
          >
            {exercicios.length === 0 && <MenuItem value="">Sem exercícios</MenuItem>}
            {exercicios.map((ex) => (
              <MenuItem key={ex.id} value={ex.id}>
                Exercício {ex.ano}
              </MenuItem>
            ))}
          </Select>

          <Select size="small" value={mes || ""} displayEmpty onChange={(e) => setMes(Number(e.target.value))} sx={{ minWidth: 160 }}>
            {!mes && <MenuItem value="">Carregando...</MenuItem>}
            {MESES.map((nome, idx) => (
              <MenuItem key={nome} value={idx + 1}>
                Até {nome}
              </MenuItem>
            ))}
          </Select>
        </Box>
        <Button variant="outlined" startIcon={<ShowChartIcon />} onClick={() => navigate("/relatorios/financeiro/graficos")}>
          Ver Gráficos
        </Button>
      </Box>

      <Box
        sx={{
          display: "flex", gap: 2, mb: 2, flexWrap: "wrap", alignItems: "center",
          position: "sticky", top: { xs: 56, sm: 64 }, zIndex: 5, bgcolor: "background.default", py: 1,
        }}
      >
        <TextField
          size="small"
          placeholder="Buscar fonte por nome ou código..."
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          sx={{ minWidth: 240 }}
        />
        <FormControlLabel
          control={<Switch checked={somenteNegativas} onChange={(e) => setSomenteNegativas(e.target.checked)} />}
          label="Só com disponibilidade líquida negativa"
        />
        <FormControlLabel
          control={<Switch checked={somenteSuperavit} onChange={(e) => setSomenteSuperavit(e.target.checked)} />}
          label="Só fontes de superávit"
        />
        <ToggleButtonGroup
          size="small"
          value={(Object.keys(blocosVisiveis) as Bloco[]).filter((b) => blocosVisiveis[b])}
          onChange={(_, novos: Bloco[]) =>
            setBlocosVisiveis({
              saldos: novos.includes("saldos"),
              execucao: novos.includes("execucao"),
              resultado: novos.includes("resultado"),
            })
          }
        >
          <ToggleButton value="saldos">Saldos Anteriores</ToggleButton>
          <ToggleButton value="execucao">Execução do Exercício</ToggleButton>
          <ToggleButton value="resultado">Resultado</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: "65vh", overflowY: "auto" }}>
        <Table size="small" sx={{ "& td, & th": { whiteSpace: "nowrap" } }}>
          <TableHead>
            <TableRow>
              <TableCell rowSpan={2} sx={{ bgcolor: "background.paper", position: "sticky", top: 0, zIndex: 4 }}>
                <TableSortLabel
                  active={ordenacao.coluna === "codigo"}
                  direction={ordenacao.coluna === "codigo" ? ordenacao.direcao : "asc"}
                  onClick={() => alternarOrdenacao("codigo")}
                >
                  Fonte
                </TableSortLabel>
              </TableCell>
              <TableCell rowSpan={2} sx={{ bgcolor: "background.paper", position: "sticky", top: 0, zIndex: 4 }}>
                <TableSortLabel
                  active={ordenacao.coluna === "nome"}
                  direction={ordenacao.coluna === "nome" ? ordenacao.direcao : "asc"}
                  onClick={() => alternarOrdenacao("nome")}
                >
                  Descrição
                </TableSortLabel>
              </TableCell>
              {(["saldos", "execucao", "resultado"] as Bloco[]).map(
                (bloco) =>
                  blocosVisiveis[bloco] && (
                    <TableCell
                      key={bloco}
                      align="center"
                      colSpan={colunas.filter((c) => c.bloco === bloco).length}
                      sx={{
                        borderLeft: 1, borderColor: "divider", bgcolor: corCabecalhoBloco[bloco],
                        height: ALTURA_LINHA_CABECALHO, position: "sticky", top: 0, zIndex: 3,
                      }}
                    >
                      {ROTULO_BLOCO[bloco]}
                    </TableCell>
                  )
              )}
            </TableRow>
            <TableRow>
              {colunasVisiveis.map((c, idx) => {
                const primeiraDoBloco = idx === 0 || colunasVisiveis[idx - 1].bloco !== c.bloco;
                return (
                  <TableCell
                    key={c.chave}
                    align="right"
                    sx={{
                      ...(primeiraDoBloco ? { borderLeft: 1, borderColor: "divider" } : {}),
                      bgcolor: corCabecalhoBloco[c.bloco],
                      position: "sticky", top: ALTURA_LINHA_CABECALHO, zIndex: 3,
                    }}
                  >
                    <TableSortLabel
                      active={ordenacao.coluna === c.chave}
                      direction={ordenacao.coluna === c.chave ? ordenacao.direcao : "desc"}
                      onClick={() => alternarOrdenacao(c.chave)}
                    >
                      {c.rotulo}
                    </TableSortLabel>
                  </TableCell>
                );
              })}
            </TableRow>
          </TableHead>
          <TableBody>
            {!carregando && gruposOrdenados.length === 0 && (
              <TableRow>
                <TableCell colSpan={2 + colunasVisiveis.length} align="center">
                  Nenhum dado para o período/filtro selecionado.
                </TableCell>
              </TableRow>
            )}
            {gruposOrdenados.map((g) => {
              const d = derivar(g);
              const caixaBrutaNegativa = d.disponibilidadeCaixaBruta < 0;
              return (
                <TableRow key={g.codigo}>
                  <TableCell
                    onClick={() => alternarSelecao(g.codigo, "codigo")}
                    sx={{ cursor: "pointer", bgcolor: corCelula(g, "codigo") }}
                  >
                    {g.codigo}
                  </TableCell>
                  <TableCell
                    onClick={() => alternarSelecao(g.codigo, "nome")}
                    sx={{ cursor: "pointer", bgcolor: corCelula(g, "nome") }}
                  >
                    {caixaBrutaNegativa && (
                      <ErrorOutlineIcon
                        fontSize="small"
                        color="error"
                        titleAccess="Disponibilidade de Caixa Bruta negativa"
                        sx={{ verticalAlign: "middle", mr: 0.5 }}
                      />
                    )}
                    {g.nome}
                  </TableCell>
                  {colunasVisiveis.map((c, idx) => {
                    const valor = c.valor(g);
                    const ehLiquida = c.chave === "disponibilidadeLiquida";
                    const liquidaNegativa = ehLiquida && valor < 0;
                    const primeiraDoBloco = idx === 0 || colunasVisiveis[idx - 1].bloco !== c.bloco;
                    return (
                      <TableCell
                        key={c.chave}
                        align="right"
                        onClick={() => alternarSelecao(g.codigo, c.chave)}
                        sx={{
                          cursor: "pointer",
                          ...(primeiraDoBloco ? { borderLeft: 1, borderColor: "divider" } : {}),
                          bgcolor: corCelula(g, c.chave),
                          color: liquidaNegativa ? "error.main" : undefined,
                          fontWeight: liquidaNegativa ? "bold" : undefined,
                        }}
                      >
                        {formatarMoeda(valor)}
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
