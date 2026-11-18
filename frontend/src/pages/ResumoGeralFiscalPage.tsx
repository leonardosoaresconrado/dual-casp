import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Box, Button, CircularProgress, Divider, MenuItem, Paper, Select, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PrintIcon from "@mui/icons-material/Print";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { api, buscarTodasPaginas } from "../api/client";
import type {
  ApuracaoASPS,
  ApuracaoDTP,
  ApuracaoETIFundeb,
  ApuracaoMagisterioFundeb,
  ApuracaoMDE,
  ApuracaoVAATDespesaCapital,
  ApuracaoVAATEducacaoInfantil,
  ApuracaoValorNaoAplicadoFundeb,
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

// As 3 únicas fontes de impostos/transferência de impostos do município —
// não existe nenhuma fonte literalmente chamada "Recursos Próprios" no
// catálogo (`FonteRecursos` não tem esse conceito, ver CLAUDE.md), confirmado
// contra o banco real antes de fixar esta lista. Nomes de fallback só para o
// caso (nunca visto até hoje) de uma dessas 3 não aparecer em nenhum saldo/
// receita/despesa do período selecionado.
const FONTES_RECURSOS_PROPRIOS: { codigo: string; nomeFallback: string }[] = [
  { codigo: "15000000", nomeFallback: "Recursos não vinculados de impostos" },
  { codigo: "15001001", nomeFallback: "Receita de imposto e transf. - Educação" },
  { codigo: "15001002", nomeFallback: "Receita de imposto e transf. - Saúde" },
];

function formatarMoeda(valor: number): string {
  const normalizado = Math.abs(valor) < 0.005 ? 0 : valor;
  return normalizado.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarPercentual(valor: number): string {
  return `${valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

// D (Devedor) soma positivo, C (Credor) soma negativo — mesma convenção de RelatorioFinanceiroPage.tsx.
function valorComSinal(valor: string, natureza: string): number {
  const n = Number(valor);
  return natureza === "C" ? -n : n;
}

interface GrupoDisponibilidade {
  codigo: string;
  nome: string;
  disponibilidadeCaixaBrutaAnterior: number;
  saldoInicialRestos: number;
  cancelamentos: number;
  pagamentosRestos: number;
  receitas: number;
  empenhos: number;
  liquidacoes: number;
  pagamentosEmpenhos: number;
}

// Mesma fórmula já validada em RelatorioFinanceiroPage.tsx
// (GrupoDisponibilidade/montarDisponibilidades/derivar) — duplicada aqui en
// vez de extraída, mesmo critério já usado ao criar
// RelatorioFinanceiroGraficosPage.tsx a partir da mesma página (2º uso,
// pequeno demais para valer a indireção de um hook compartilhado). Omite os
// campos "Saldo Final RPNP/RP (estimado)" do original — só servem para
// exibição em colunas daquela tabela, não entram em nenhuma fórmula de
// derivar() e não são mostrados neste resumo.
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
        cancelamentos: 0, pagamentosRestos: 0, receitas: 0, empenhos: 0, liquidacoes: 0, pagamentosEmpenhos: 0,
      });
    }
    return mapa.get(codigo)!;
  }

  for (const c of saldosAbertura) {
    for (const f of c.fontes) {
      grupo(f.fonte_recursos_codigo, f.fonte_recursos_nome).disponibilidadeCaixaBrutaAnterior +=
        valorComSinal(f.valor, f.natureza);
    }
  }

  for (const r of restosAPagarTodos) {
    if (r.mes_referencia !== 1) continue;
    grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome).saldoInicialRestos +=
      Number(r.inscricao_processada) + Number(r.inscricao_nao_processada) + Number(r.reinscricao);
  }

  for (const r of restosAPagarTodos) {
    if (r.mes_referencia !== mes) continue;
    const g = grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome);
    g.cancelamentos += Number(r.cancelamento);
    g.pagamentosRestos += Number(r.rpp_pago) + Number(r.rpnp_pago);
  }

  for (const l of lancamentosReceita) {
    if (l.mes_referencia > mes) continue;
    const r = l.rubrica_detalhe;
    grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome).receitas += Number(l.valor_liquido_no_mes);
  }

  for (const l of lancamentosDespesa) {
    const r = l.rubrica_detalhe;
    const g = grupo(r.fonte_recursos_codigo, r.fonte_recursos_nome);
    g.empenhos += Number(l.empenhado_acumulado);
    g.liquidacoes += Number(l.liquidado_acumulado);
    g.pagamentosEmpenhos += Number(l.pago_acumulado);
  }

  return Array.from(mapa.values());
}

function derivarDisponibilidades(g: GrupoDisponibilidade): { disponibilidadeCaixaBruta: number; disponibilidadeLiquida: number } {
  const saldoRestosFinal = g.saldoInicialRestos - g.cancelamentos - g.pagamentosRestos;
  const inscricaoRPNP = g.empenhos - g.liquidacoes;
  const inscricaoRP = g.liquidacoes - g.pagamentosEmpenhos;
  const ingressos = g.disponibilidadeCaixaBrutaAnterior + g.receitas;
  const dispendios = g.pagamentosRestos + g.pagamentosEmpenhos;
  const disponibilidadeCaixaBruta = ingressos - dispendios;
  const disponibilidadeLiquida = disponibilidadeCaixaBruta - (inscricaoRPNP + inscricaoRP) - saldoRestosFinal;
  return { disponibilidadeCaixaBruta, disponibilidadeLiquida };
}

function LinhaResumo({
  rotulo,
  valor,
  cumprido,
  indentado,
  negrito,
  corValor,
}: {
  rotulo: string;
  valor: string;
  cumprido?: boolean | null;
  indentado?: boolean;
  negrito?: boolean;
  // Cor do próprio texto do valor — verde/vermelho para indicar
  // acima/abaixo do limite (índices, via `cumprido`) ou positivo/negativo
  // (valores monetários com sinal, ex. déficit/superávit). `undefined` =
  // sem dado ainda (nunca colore "Sem dados"); `null` = cor neutra mesmo
  // havendo dado (ex. totais sem noção de "bom"/"ruim", como Total Arrecadado).
  corValor?: "success.main" | "error.main" | null;
}) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, py: 0.5, pl: indentado ? 3 : 0 }}>
      <Typography variant="body2" sx={{ fontWeight: negrito ? 700 : 400 }}>
        {rotulo}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: negrito ? 700 : 400, color: corValor ?? undefined }}>
          {valor}
        </Typography>
        {cumprido !== null && cumprido !== undefined && (
          <Typography component="span" sx={{ color: cumprido ? "success.main" : "error.main", fontWeight: 700 }}>
            {cumprido ? "✓" : "✗"}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

// `cumprido` → verde se true, vermelho se false, neutro se ainda não há
// dado (`null`/`undefined`) — usada nas linhas de índice único, onde
// `cumpre_limite` já diz diretamente se está acima/abaixo do exigido.
function corPorConformidade(cumprido: boolean | null | undefined): "success.main" | "error.main" | null {
  return cumprido === null || cumprido === undefined ? null : cumprido ? "success.main" : "error.main";
}

// Usada nas 3 sub-linhas de Educação (Empenhada/Liquidada/Paga) — essas 3
// fases não têm `cumpre_limite` próprio (só o percentual STN oficial,
// `ApuracaoMDE.cumpre_limite`, tem), mas o mínimo de 25% da Constituição
// vale igualmente para qualquer uma das 3 bases, então compara cada
// percentual diretamente contra o mesmo piso.
function corPorMinimo(valor: number | null, minimo: number): "success.main" | "error.main" | null {
  return valor === null ? null : valor >= minimo ? "success.main" : "error.main";
}

// Sinal do valor em si (déficit/superávit, disponibilidade negativa) →
// verde se ≥ 0, vermelho se negativo.
function corPorSinal(valor: number | null): "success.main" | "error.main" | null {
  return valor === null ? null : valor >= 0 ? "success.main" : "error.main";
}

export function ResumoGeralFiscalPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { municipioSelecionadoId, municipios } = useScope();
  const conteudoRef = useRef<HTMLDivElement>(null);
  const [gerandoPdf, setGerandoPdf] = useState(false);

  const [exercicios, setExercicios] = useState<Exercicio[]>([]);
  const [exercicioId, setExercicioId] = useState<number | "">("");
  // 0 = ainda não escolhido — assim que o MDE do exercício carregar, um
  // efeito abaixo escolhe o bimestre mais recente com dado automaticamente.
  const [bimestre, setBimestre] = useState<number>(0);

  const [dtp, setDtp] = useState<ApuracaoDTP[]>([]);
  const [mde, setMde] = useState<ApuracaoMDE[]>([]);
  const [magisterio, setMagisterio] = useState<ApuracaoMagisterioFundeb[]>([]);
  const [eti, setEti] = useState<ApuracaoETIFundeb[]>([]);
  const [asps, setAsps] = useState<ApuracaoASPS[]>([]);
  const [vaatEdInfantil, setVaatEdInfantil] = useState<ApuracaoVAATEducacaoInfantil[]>([]);
  const [vaatCapital, setVaatCapital] = useState<ApuracaoVAATDespesaCapital[]>([]);
  const [fundebNaoAplicado, setFundebNaoAplicado] = useState<ApuracaoValorNaoAplicadoFundeb[]>([]);

  const [saldosAbertura, setSaldosAbertura] = useState<SaldoBalancoConta[]>([]);
  const [lancamentosReceita, setLancamentosReceita] = useState<LancamentoExecucaoReceita[]>([]);
  const [lancamentosDespesa, setLancamentosDespesa] = useState<LancamentoExecucaoOrcamentaria[]>([]);
  const [restosAPagar, setRestosAPagar] = useState<RestoAPagar[]>([]);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get<{ results: Exercicio[] }>("/exercicios/", { params: { municipio: municipioSelecionadoId } })
      .then(({ data }) => {
        const anoParam = searchParams.get("exercicio");
        const correspondente = anoParam ? data.results.find((e) => String(e.ano) === anoParam) : null;
        setExercicios(data.results);
        setExercicioId((correspondente ?? data.results[0])?.id ?? "");
      });
    buscarTodasPaginas<SaldoBalancoConta>("/saldo-balanco/", {}).then((todas) => {
      const dataAbertura = todas.map((c) => c.data_referencia).sort()[0];
      setSaldosAbertura(todas.filter((c) => c.data_referencia === dataAbertura));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [municipioSelecionadoId]);

  const exercicioSelecionado = useMemo(
    () => exercicios.find((e) => e.id === exercicioId) ?? null,
    [exercicios, exercicioId]
  );

  const municipioNome = useMemo(() => {
    const m = municipios.find((mu) => mu.id === municipioSelecionadoId);
    return m ? `${m.nome}/${m.uf}` : "";
  }, [municipios, municipioSelecionadoId]);

  useEffect(() => {
    setBimestre(0);
    if (!municipioSelecionadoId || !exercicioSelecionado) return;
    const params = { municipio: municipioSelecionadoId, exercicio: exercicioSelecionado.ano };
    buscarTodasPaginas<ApuracaoDTP>("/apuracao-dtp/", params).then(setDtp);
    buscarTodasPaginas<ApuracaoMDE>("/apuracao-mde/", params).then(setMde);
    buscarTodasPaginas<ApuracaoMagisterioFundeb>("/apuracao-magisterio-fundeb/", params).then(setMagisterio);
    buscarTodasPaginas<ApuracaoETIFundeb>("/apuracao-fundeb-eti/", params).then(setEti);
    buscarTodasPaginas<ApuracaoASPS>("/apuracao-asps/", params).then(setAsps);
    buscarTodasPaginas<ApuracaoVAATEducacaoInfantil>("/apuracao-vaat-educacao-infantil/", params).then(setVaatEdInfantil);
    buscarTodasPaginas<ApuracaoVAATDespesaCapital>("/apuracao-vaat-despesa-capital/", params).then(setVaatCapital);
    buscarTodasPaginas<ApuracaoValorNaoAplicadoFundeb>("/apuracao-fundeb-nao-aplicado/", params).then(setFundebNaoAplicado);
  }, [municipioSelecionadoId, exercicioSelecionado]);

  // Bimestre mais recente com dado em MDE (índice mais completo) — mesmo
  // critério "sort desc, pega o primeiro" já usado em ExecucaoFiscalPage.tsx.
  // Só decide sozinho enquanto o usuário ainda não escolheu nada (bimestre === 0).
  useEffect(() => {
    if (bimestre !== 0 || mde.length === 0) return;
    const maisRecente = mde.slice().sort((a, b) => b.bimestre - a.bimestre)[0];
    setBimestre(maisRecente.bimestre);
  }, [mde, bimestre]);

  // Mês de fechamento do bimestre (1→Fev, 2→Abr, ..., 6→Dez) — mesma
  // convenção já usada nos parsers de RGF/RREO (bimestre = ceil(mês/2)).
  const mesFechamento = bimestre * 2;

  useEffect(() => {
    if (!exercicioSelecionado?.loa_id || !mesFechamento) {
      setLancamentosReceita([]);
      setLancamentosDespesa([]);
      setRestosAPagar([]);
      return;
    }
    const loaId = exercicioSelecionado.loa_id;
    let cancelado = false;
    Promise.all([
      buscarTodasPaginas<LancamentoExecucaoReceita>("/execucao-receita/", { loa: loaId, mes_referencia_ate: mesFechamento }),
      buscarTodasPaginas<LancamentoExecucaoOrcamentaria>("/execucao-orcamentaria/", { loa: loaId, mes_referencia: mesFechamento }),
      buscarTodasPaginas<RestoAPagar>("/restos-a-pagar/", { mes_referencia: 1 }),
      mesFechamento === 1
        ? Promise.resolve<RestoAPagar[]>([])
        : buscarTodasPaginas<RestoAPagar>("/restos-a-pagar/", { mes_referencia: mesFechamento }),
    ]).then(([receita, despesa, restosMes1, restosMesAtual]) => {
      if (cancelado) return;
      setLancamentosReceita(receita);
      setLancamentosDespesa(despesa);
      setRestosAPagar([...restosMes1, ...restosMesAtual]);
    });
    return () => {
      cancelado = true;
    };
  }, [exercicioSelecionado, mesFechamento]);

  const grupos = useMemo(
    () => montarDisponibilidades(saldosAbertura, restosAPagar, lancamentosReceita, lancamentosDespesa, mesFechamento),
    [saldosAbertura, restosAPagar, lancamentosReceita, lancamentosDespesa, mesFechamento]
  );

  const totais = useMemo(() => {
    let disponibilidadeCaixaBruta = 0;
    let disponibilidadeLiquida = 0;
    let receitas = 0;
    let empenhos = 0;
    for (const g of grupos) {
      const d = derivarDisponibilidades(g);
      disponibilidadeCaixaBruta += d.disponibilidadeCaixaBruta;
      disponibilidadeLiquida += d.disponibilidadeLiquida;
      receitas += g.receitas;
      empenhos += g.empenhos;
    }
    return { disponibilidadeCaixaBruta, disponibilidadeLiquida, receitas, empenhos };
  }, [grupos]);

  const recursosProprios = useMemo(
    () =>
      FONTES_RECURSOS_PROPRIOS.map(({ codigo, nomeFallback }) => {
        const g = grupos.find((grupo) => grupo.codigo === codigo) ?? null;
        return {
          codigo,
          nome: g?.nome ?? nomeFallback,
          disponibilidadeLiquida: g ? derivarDisponibilidades(g).disponibilidadeLiquida : null,
        };
      }),
    [grupos]
  );
  const recursosPropriosTotal = useMemo(
    () => recursosProprios.reduce((acc, r) => acc + (r.disponibilidadeLiquida ?? 0), 0),
    [recursosProprios]
  );

  function acharPorBimestre<T extends { bimestre: number }>(lista: T[]): T | null {
    return lista.find((d) => d.bimestre === bimestre) ?? null;
  }

  const dtpB = acharPorBimestre(dtp);
  const mdeB = acharPorBimestre(mde);
  const magisterioB = acharPorBimestre(magisterio);
  const etiB = acharPorBimestre(eti);
  const aspsB = acharPorBimestre(asps);
  const vaatEdInfantilB = acharPorBimestre(vaatEdInfantil);
  const vaatCapitalB = acharPorBimestre(vaatCapital);
  const fundebNaoAplicadoB = acharPorBimestre(fundebNaoAplicado);

  const rotuloVaatEdInfantil = vaatEdInfantilB?.percentual_vaat_publicado
    ? `Índice IEI ${formatarPercentual(Number(vaatEdInfantilB.percentual_vaat_publicado))} do VAAT`
    : "Índice IEI do VAAT (Educação Infantil)";

  // Gera um .pdf de verdade (não só o diálogo de impressão do navegador) a
  // partir do conteúdo já renderizado (`conteudoRef`): html2canvas tira uma
  // captura em alta resolução (escala 2x, fundo branco — a Paper por padrão
  // é transparente em tema escuro, mas este app nunca liga modo escuro, ver
  // CLAUDE.md) e jsPDF fatia essa imagem em páginas A4, repetindo a largura
  // útil (210mm − 20mm de margem) e avançando a altura visível a cada página
  // — mesmo padrão de paginação de imagem única já usado por qualquer
  // integração jsPDF+html2canvas. Carregadas via import() dinâmico (não no
  // bundle principal) já que só este botão as usa.
  async function baixarPdf() {
    if (!conteudoRef.current) return;
    setGerandoPdf(true);
    try {
      const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
        import("jspdf"),
        import("html2canvas"),
      ]);
      const canvas = await html2canvas(conteudoRef.current, { scale: 2, backgroundColor: "#ffffff" });
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const margem = 10;
      const larguraUtil = pdf.internal.pageSize.getWidth() - margem * 2;
      const alturaUtil = pdf.internal.pageSize.getHeight() - margem * 2;
      const alturaImagem = (canvas.height * larguraUtil) / canvas.width;
      const imagem = canvas.toDataURL("image/png");

      let alturaRestante = alturaImagem;
      let deslocamento = 0;
      pdf.addImage(imagem, "PNG", margem, margem, larguraUtil, alturaImagem);
      alturaRestante -= alturaUtil;
      while (alturaRestante > 0) {
        deslocamento += alturaUtil;
        pdf.addPage();
        pdf.addImage(imagem, "PNG", margem, margem - deslocamento, larguraUtil, alturaImagem);
        alturaRestante -= alturaUtil;
      }

      const sufixoMunicipio = municipioNome.split("/")[0].trim().replace(/\s+/g, "_") || "municipio";
      pdf.save(`resumo-geral-execucao-fiscal-${sufixoMunicipio}-${exercicioSelecionado?.ano ?? ""}-${bimestre}bim.pdf`);
    } finally {
      setGerandoPdf(false);
    }
  }

  return (
    <Box>
      <Box className="no-imprimir" sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/execucao-fiscal")}>
            Voltar
          </Button>
          <Typography variant="h5">Resumo Geral — Execução Fiscal</Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={gerandoPdf ? <CircularProgress size={16} /> : <PictureAsPdfIcon />}
            disabled={gerandoPdf}
            onClick={baixarPdf}
          >
            {gerandoPdf ? "Gerando..." : "Baixar PDF"}
          </Button>
          <Button variant="contained" startIcon={<PrintIcon />} onClick={() => window.print()}>
            Imprimir
          </Button>
        </Box>
      </Box>

      <Box className="no-imprimir" sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
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
        <Select size="small" value={bimestre || ""} displayEmpty onChange={(e) => setBimestre(Number(e.target.value))} sx={{ minWidth: 160 }}>
          {!bimestre && <MenuItem value="">Carregando...</MenuItem>}
          {[1, 2, 3, 4, 5, 6].map((b) => (
            <MenuItem key={b} value={b}>
              {b}º Bimestre (até {MESES[b * 2 - 1]})
            </MenuItem>
          ))}
        </Select>
      </Box>

      <Paper ref={conteudoRef} sx={{ p: 4, maxWidth: 820, mx: "auto" }}>
        <Typography variant="h6" gutterBottom>
          Resumo Geral da Execução Fiscal
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {municipioNome || "Município não selecionado"} — Exercício {exercicioSelecionado?.ano ?? "—"} — {bimestre || "—"}º Bimestre
          {bimestre ? ` (até ${MESES[mesFechamento - 1]}/${exercicioSelecionado?.ano})` : ""}
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" sx={{ fontWeight: 700 }} gutterBottom>
          ÍNDICES (%)
        </Typography>
        <LinhaResumo
          rotulo="Índice de Aplicação em Educação (desconsiderando PNAE/PEAE e Ensino Médio/Superior):"
          valor=""
          negrito
        />
        <LinhaResumo
          rotulo="Sobre a despesa Empenhada"
          valor={mdeB ? formatarPercentual(Number(mdeB.indice_gerencial_2_desconsiderando_pnae)) : "Sem dados"}
          corValor={mdeB ? corPorMinimo(Number(mdeB.indice_gerencial_2_desconsiderando_pnae), 25) : null}
          cumprido={mdeB ? Number(mdeB.indice_gerencial_2_desconsiderando_pnae) >= 25 : null}
          indentado
        />
        <LinhaResumo
          rotulo="Sobre a despesa Liquidada"
          valor={mdeB ? formatarPercentual(Number(mdeB.indice_gerencial_1_desconsiderando_pnae)) : "Sem dados"}
          corValor={mdeB ? corPorMinimo(Number(mdeB.indice_gerencial_1_desconsiderando_pnae), 25) : null}
          cumprido={mdeB ? Number(mdeB.indice_gerencial_1_desconsiderando_pnae) >= 25 : null}
          indentado
        />
        <LinhaResumo
          rotulo="Sobre a despesa Paga"
          valor={mdeB ? formatarPercentual(Number(mdeB.indice_gerencial_3_desconsiderando_pnae)) : "Sem dados"}
          corValor={mdeB ? corPorMinimo(Number(mdeB.indice_gerencial_3_desconsiderando_pnae), 25) : null}
          cumprido={mdeB ? Number(mdeB.indice_gerencial_3_desconsiderando_pnae) >= 25 : null}
          indentado
        />
        <LinhaResumo
          rotulo="Índice de Aplicação em Saúde (ASPS)"
          valor={aspsB ? formatarPercentual(Number(aspsB.percentual_aplicado)) : "Sem dados"}
          cumprido={aspsB?.cumpre_limite}
          corValor={corPorConformidade(aspsB?.cumpre_limite)}
        />
        <LinhaResumo
          rotulo="Índice de Aplicação em Pessoal (DTP)"
          valor={dtpB ? formatarPercentual(Number(dtpB.percentual_dtp)) : "Sem dados"}
          cumprido={dtpB?.cumpre_limite}
          corValor={corPorConformidade(dtpB?.cumpre_limite)}
        />
        <LinhaResumo
          rotulo="Índice 70% do Fundeb (Magistério)"
          valor={magisterioB ? formatarPercentual(Number(magisterioB.percentual_aplicado)) : "Sem dados"}
          cumprido={magisterioB?.cumpre_limite}
          corValor={corPorConformidade(magisterioB?.cumpre_limite)}
        />
        <LinhaResumo
          rotulo={rotuloVaatEdInfantil}
          valor={vaatEdInfantilB ? formatarPercentual(Number(vaatEdInfantilB.percentual_aplicado)) : "Sem dados"}
          cumprido={vaatEdInfantilB?.cumpre_limite}
          corValor={corPorConformidade(vaatEdInfantilB?.cumpre_limite)}
        />
        <LinhaResumo
          rotulo="Índice 15% do VAAT (Despesa de Capital)"
          valor={vaatCapitalB ? formatarPercentual(Number(vaatCapitalB.percentual_aplicado)) : "Sem dados"}
          cumprido={vaatCapitalB?.cumpre_limite}
          corValor={corPorConformidade(vaatCapitalB?.cumpre_limite)}
        />
        <LinhaResumo
          rotulo="Índice ETI 4%"
          valor={etiB ? formatarPercentual(Number(etiB.percentual_aplicado)) : "Sem dados"}
          cumprido={etiB?.cumpre_limite}
          corValor={corPorConformidade(etiB?.cumpre_limite)}
        />
        <LinhaResumo
          rotulo="Índice Máx. 10% Não Aplicado FUNDEB"
          valor={fundebNaoAplicadoB ? formatarPercentual(Number(fundebNaoAplicadoB.percentual_nao_aplicado)) : "Sem dados"}
          cumprido={fundebNaoAplicadoB?.cumpre_limite}
          corValor={corPorConformidade(fundebNaoAplicadoB?.cumpre_limite)}
        />

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" sx={{ fontWeight: 700 }} gutterBottom>
          VALORES (R$)
        </Typography>
        <LinhaResumo
          rotulo="Disponibilidade de Caixa Bruta"
          valor={formatarMoeda(totais.disponibilidadeCaixaBruta)}
          corValor={corPorSinal(totais.disponibilidadeCaixaBruta)}
        />
        <LinhaResumo
          rotulo="Disponibilidade de Caixa Líquida"
          valor={formatarMoeda(totais.disponibilidadeLiquida)}
          corValor={corPorSinal(totais.disponibilidadeLiquida)}
        />
        <LinhaResumo rotulo="Total Arrecadado" valor={formatarMoeda(totais.receitas)} />
        <LinhaResumo rotulo="Total Empenhado" valor={formatarMoeda(totais.empenhos)} />
        <LinhaResumo
          rotulo="Total de Gasto com Pessoal"
          valor={dtpB ? formatarMoeda(Number(dtpB.despesa_total_pessoal)) : "Sem dados"}
        />
        <LinhaResumo
          rotulo="Receita Corrente Líquida"
          valor={dtpB ? formatarMoeda(Number(dtpB.rcl)) : "Sem dados"}
        />
        <LinhaResumo
          rotulo="Receita Corrente Líquida para Fins de Gasto com Pessoal"
          valor={dtpB ? formatarMoeda(Number(dtpB.rcl_ajustada)) : "Sem dados"}
        />

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" sx={{ fontWeight: 700 }} gutterBottom>
          DISPONIBILIDADES DOS RECURSOS PRÓPRIOS
        </Typography>
        <LinhaResumo
          rotulo={`${recursosPropriosTotal >= 0 ? "Superávit" : "Déficit"} Total (sendo:)`}
          valor={formatarMoeda(recursosPropriosTotal)}
          corValor={corPorSinal(recursosPropriosTotal)}
          negrito
        />
        {recursosProprios.map((r) => (
          <LinhaResumo
            key={r.codigo}
            rotulo={`${r.codigo} - ${r.nome}`}
            valor={
              r.disponibilidadeLiquida === null
                ? "Sem dados"
                : `${r.disponibilidadeLiquida >= 0 ? "Superávit" : "Déficit"} de ${formatarMoeda(r.disponibilidadeLiquida)}`
            }
            corValor={corPorSinal(r.disponibilidadeLiquida)}
            indentado
          />
        ))}
      </Paper>
    </Box>
  );
}
