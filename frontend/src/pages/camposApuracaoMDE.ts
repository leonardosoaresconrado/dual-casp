import type { CampoEdicao } from "../components/AcoesRegistroManual";

// Campos editáveis de ApuracaoMDE, compartilhados entre ExecucaoFiscalPage.tsx
// (diálogo "Novo" da visão sintética) e ExecucaoFiscalDetalhadoPage.tsx
// (edição do 6º bimestre projetado) — extraído em vez de duplicado porque são
// literalmente os mesmos campos do mesmo model editados nos dois lugares; se
// um ganhar um campo novo (ex. uma futura dedução) e o outro não acompanhar,
// os dois formulários silenciosamente divergem.
export const CAMPOS_MDE: CampoEdicao[] = [
  { chave: "receita_impostos", rotulo: "1 - Receita de Impostos", tipo: "decimal" },
  { chave: "receita_transferencias", rotulo: "2 - Receita de Transferências", tipo: "decimal" },
  { chave: "base_calculo", rotulo: "Base de Cálculo", tipo: "decimal" },
  { chave: "minimo_constitucional", rotulo: "Mínimo Constitucional (25%)", tipo: "decimal" },
  { chave: "despesa_mde_empenhada", rotulo: "(+) MDE Empenhado", tipo: "decimal" },
  { chave: "despesa_mde_liquidada", rotulo: "(+) MDE Liquidado", tipo: "decimal" },
  { chave: "despesa_mde_paga", rotulo: "(+) MDE Pago", tipo: "decimal" },
  { chave: "fundeb_transferido", rotulo: "(+) FUNDEB Transferido", tipo: "decimal" },
  { chave: "excedente_fundeb_nao_aplicado", rotulo: "(-) Excedente FUNDEB Não Aplicado", tipo: "decimal" },
  { chave: "cancelamento_rp", rotulo: "(-) Cancelamento de RP", tipo: "decimal" },
  {
    chave: "aplicacao_pnae_recursos_proprios",
    rotulo: "(-) Aplicação no PNAE/PEAE de Recursos Próprios (gerencial)",
    tipo: "decimal",
  },
  {
    chave: "despesa_ensino_medio_superior_recursos_proprios",
    rotulo: "(-) Despesa com Ensino Médio/Superior (362/364) em Recursos Próprios (gerencial)",
    tipo: "decimal",
  },
  { chave: "valor_exigido", rotulo: "Valor Exigido", tipo: "decimal" },
  { chave: "valor_aplicado", rotulo: "Valor Aplicado (TOTAL STN)", tipo: "decimal" },
  { chave: "percentual_aplicado", rotulo: "% Aplicado (ÍNDICE STN)", tipo: "decimal" },
];
