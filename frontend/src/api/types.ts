export interface VinculoAcesso {
  id: number;
  usuario?: number;
  usuario_nome?: string;
  municipio: number;
  municipio_nome: string;
  unidade_gestora: number | null;
  unidade_gestora_nome: string | null;
  orgao: number | null;
  orgao_nome: string | null;
  papel: "ADMIN" | "GESTOR" | "ANALISTA" | "VISUALIZACAO";
}

export interface Usuario {
  id: number;
  cpf: string;
  cpf_formatado: string;
  nome_completo: string;
  email: string;
  telefone: string;
  is_equipe_escritorio: boolean;
  is_active: boolean;
  vinculos_acesso: VinculoAcesso[];
}

export type SistemaOrigemImportacao = "ASPEC";
export type TipoRelatorioImportacao =
  | "EXECUCAO_ORCAMENTARIA"
  | "EXECUCAO_FINANCEIRA"
  | "RESTOS_A_PAGAR"
  | "INDICADORES_FISCAIS";
export type StatusImportacao = "PENDENTE" | "PROCESSANDO" | "CONCLUIDA" | "ERRO";

export interface Importacao {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number | null;
  sistema_origem: SistemaOrigemImportacao;
  sistema_origem_label: string;
  tipo_relatorio: TipoRelatorioImportacao;
  tipo_relatorio_label: string;
  arquivo: string;
  status: StatusImportacao;
  status_label: string;
  mensagem_erro: string;
  linhas_importadas: number;
  usuario: number;
  usuario_nome: string;
  criado_em: string;
  processado_em: string | null;
}

export interface Municipio {
  id: number;
  nome: string;
  uf: string;
  codigo_ibge: string;
  ativo: boolean;
}

export interface Parametro {
  id: number;
  chave: string;
  descricao: string;
  valor_booleano: boolean;
}

export interface UnidadeGestora {
  id: number;
  municipio: number;
  codigo: string;
  nome: string;
  poder: "EXECUTIVO" | "LEGISLATIVO";
  cnpj: string;
  ativo: boolean;
}

export interface Exercicio {
  id: number;
  municipio: number;
  municipio_nome: string;
  ano: number;
  status: "PLANEJAMENTO" | "EM_EXECUCAO" | "ENCERRADO";
  loa_id: number | null;
}

export type OrigemDotacao =
  | "ORCAMENTO"
  | "CREDITO_SUPLEMENTAR"
  | "CREDITO_ESPECIAL"
  | "CREDITO_ADICIONAL";

export type OrigemRegistro = "IMPORTADO" | "MANUAL";

export interface CampoOrigemRegistro {
  origem_registro: OrigemRegistro;
  criado_por: number | null;
  atualizado_por: number | null;
}

export interface RubricaDetalhe extends CampoOrigemRegistro {
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
  subelemento_nome: string;
  fonte_recursos_codigo: string;
  fonte_recursos_nome: string;
  dotacao_inicial: string;
  origem_dotacao: OrigemDotacao;
  origem_dotacao_label: string;
}

export interface RubricaOrcamentaria extends RubricaDetalhe {
  id: number;
  loa: number;
}

export interface LancamentoExecucaoOrcamentaria extends CampoOrigemRegistro {
  id: number;
  rubrica: number;
  rubrica_detalhe: RubricaDetalhe;
  mes_referencia: number;
  dotacao_inicial: string;
  creditos_suplementares: string;
  creditos_especiais: string;
  anulacoes: string;
  dotacao_atualizada: string;
  empenhado_no_mes: string;
  empenhado_acumulado: string;
  liquidado_no_mes: string;
  liquidado_acumulado: string;
  pago_no_mes: string;
  pago_acumulado: string;
  saldo_a_empenhar: string;
  saldo_a_liquidar: string;
  saldo_a_pagar: string;
}

export interface EmpenhoMovimento {
  id: number;
  mes_referencia: number;
  valor_empenho_no_mes: string;
  valor_liquidado_no_mes: string;
  valor_pago_no_mes: string;
}

export interface Empenho extends CampoOrigemRegistro {
  id: number;
  unidade_gestora: number;
  unidade_gestora_nome: string;
  rubrica: number;
  numero: string;
  data_empenho: string;
  credor: string;
  historico: string;
  valor_empenho: string;
  valor_liquidado: string;
  valor_pago: string;
  saldo_a_liquidar: string;
  saldo_a_pagar: string;
  movimentos: EmpenhoMovimento[];
}

export interface RubricaReceita extends CampoOrigemRegistro {
  id: number;
  loa: number;
  unidade_gestora: number;
  unidade_gestora_nome: string;
  codigo: string;
  nome: string;
  fonte_recursos: number;
  fonte_recursos_codigo: string;
  fonte_recursos_nome: string;
  valor_orcado: string;
  classificacao_tipo: number | null;
  classificacao_tipo_codigo: string | null;
  detalhamento_adicional: string;
  eh_deducao: boolean;
  rubrica_principal: number | null;
  rubrica_principal_codigo: string | null;
}

export type OrigemClassificacao = "OFICIAL" | "MUNICIPAL";

export interface CampoClassificacaoOficial {
  ativo: boolean;
  origem_classificacao: OrigemClassificacao;
  ano_vigencia_inicial: number | null;
  criado_em: string;
  atualizado_em: string;
}

// Categoria Econômica (nível 1) é compartilhada com a despesa — ver
// apps.orcamento.CategoriaEconomica no backend. Não tem interface TS
// própria aqui porque os cadastros usam CrudManager com tipagem solta.

export interface ClassificacaoReceitaOrigem extends CampoClassificacaoOficial {
  id: number;
  categoria: number;
  categoria_codigo: string;
  codigo: string;
  nome: string;
}

export interface ClassificacaoReceitaEspecie extends CampoClassificacaoOficial {
  id: number;
  origem: number;
  origem_codigo: string;
  codigo: string;
  nome: string;
}

export interface ClassificacaoReceitaRubrica extends CampoClassificacaoOficial {
  id: number;
  especie: number;
  especie_codigo: string;
  codigo: string;
  nome: string;
}

export interface ClassificacaoReceitaAlinea extends CampoClassificacaoOficial {
  id: number;
  rubrica: number;
  rubrica_codigo: string;
  codigo: string;
  nome: string;
}

export interface ClassificacaoReceitaSubalinea extends CampoClassificacaoOficial {
  id: number;
  alinea: number;
  alinea_codigo: string;
  codigo: string;
  nome: string;
}

export interface ClassificacaoReceitaTipo extends CampoClassificacaoOficial {
  id: number;
  subalinea: number;
  subalinea_codigo: string;
  codigo: string;
  nome: string;
}

export interface LancamentoExecucaoReceita extends CampoOrigemRegistro {
  id: number;
  rubrica: number;
  rubrica_detalhe: RubricaReceita;
  mes_referencia: number;
  valor_bruto_no_mes: string;
  deducao_no_mes: string;
  anulacao_no_mes: string;
  valor_liquido_no_mes: string;
}

export type NaturezaSaldo = "D" | "C";

export interface SaldoBalancoContaFonte {
  id: number;
  fonte_recursos: number;
  fonte_recursos_codigo: string;
  fonte_recursos_nome: string;
  valor: string;
  natureza: NaturezaSaldo;
}

export interface SaldoBalancoConta extends CampoOrigemRegistro {
  id: number;
  unidade_gestora: number;
  unidade_gestora_nome: string;
  data_referencia: string;
  categoria: string;
  codigo_conta: string;
  banco: string;
  numero_conta: string;
  apelido: string;
  valor: string;
  natureza: NaturezaSaldo;
  fontes: SaldoBalancoContaFonte[];
}

export interface SaldoContaBancariaFonte {
  id: number;
  fonte_recursos: number;
  fonte_recursos_codigo: string;
  fonte_recursos_nome: string;
  valor: string;
  natureza: NaturezaSaldo | "";
}

export interface SaldoContaBancaria extends CampoOrigemRegistro {
  id: number;
  unidade_gestora: number;
  unidade_gestora_nome: string;
  mes_referencia: number;
  data_referencia: string;
  banco: string;
  numero_conta: string;
  apelido: string;
  saldo_pre_pagamentos_previstos: string;
  saldo_nao_comprometido: string;
  fontes: SaldoContaBancariaFonte[];
}

export interface RestoAPagar extends CampoOrigemRegistro {
  id: number;
  unidade_gestora: number;
  unidade_gestora_nome: string;
  fonte_recursos: number;
  fonte_recursos_codigo: string;
  fonte_recursos_nome: string;
  mes_referencia: number;
  exercicio_origem: number;
  numero_empenho: string;
  inscricao_processada: string;
  inscricao_nao_processada: string;
  reinscricao: string;
  cancelamento: string;
  liquidacao: string;
  rpp_pago: string;
  rpnp_pago: string;
  pago_total: string;
  credor_nome: string;
  orgao: number | null;
  orgao_nome: string;
  unidade_orcamentaria: number | null;
  unidade_orcamentaria_nome: string;
  elemento_despesa: number | null;
  elemento_despesa_codigo: string;
  elemento_despesa_nome: string;
  classificacao_funcional_programatica: string;
  acao_nome: string;
  classificacao_economica_codigo: string;
}

export interface ApuracaoDTP extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  rcl: string;
  deducao_emendas_individuais: string;
  deducao_emendas_bancada: string;
  deducao_agentes_saude: string;
  deducao_outras: string;
  deducoes_rcl: string;
  rcl_ajustada: string;
  despesa_total_pessoal: string;
  percentual_dtp: string;
  limite_maximo_valor: string;
  limite_maximo_percentual: string;
  limite_prudencial_valor: string;
  limite_prudencial_percentual: string;
  limite_alerta_valor: string;
  limite_alerta_percentual: string;
  cumpre_limite: boolean;
}

export interface ApuracaoMDEReceitaItem {
  id: number;
  grupo: "IMPOSTOS" | "TRANSFERENCIAS";
  codigo: string;
  rotulo: string;
  valor: string;
}

export interface ApuracaoMDE extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  receita_impostos: string;
  receita_transferencias: string;
  itens_receita: ApuracaoMDEReceitaItem[];
  base_calculo: string;
  minimo_constitucional: string;
  despesa_mde_empenhada: string;
  despesa_mde_liquidada: string;
  despesa_mde_paga: string;
  fundeb_transferido: string;
  excedente_fundeb_nao_aplicado: string;
  cancelamento_rp: string;
  aplicacao_pnae_recursos_proprios: string;
  despesa_ensino_medio_superior_recursos_proprios: string;
  valor_exigido: string;
  valor_aplicado: string;
  percentual_aplicado: string;
  total_gerencial_1: string;
  total_gerencial_2: string;
  total_gerencial_3: string;
  indice_gerencial_1: string | null;
  indice_gerencial_2: string | null;
  indice_gerencial_3: string | null;
  total_gerencial_1_desconsiderando_pnae: string;
  total_gerencial_2_desconsiderando_pnae: string;
  total_gerencial_3_desconsiderando_pnae: string;
  indice_gerencial_1_desconsiderando_pnae: string | null;
  indice_gerencial_2_desconsiderando_pnae: string | null;
  indice_gerencial_3_desconsiderando_pnae: string | null;
  cumpre_limite: boolean;
}

export interface ApuracaoMagisterioFundeb extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  fundeb_receita_total: string;
  valor_exigido: string;
  valor_aplicado: string;
  percentual_aplicado: string;
  cumpre_limite: boolean;
}

export interface ApuracaoETIFundeb extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  fundeb_receita_total: string;
  valor_exigido: string;
  valor_aplicado: string;
  percentual_aplicado: string;
  cumpre_limite: boolean;
}

export interface ApuracaoASPS extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  receita_impostos_transferencias: string;
  base_calculo: string;
  minimo_constitucional: string;
  despesa_asps_empenhada: string;
  despesa_asps_liquidada: string;
  despesa_asps_paga: string;
  percentual_aplicado: string;
  percentual_gerencial: string | null;
  cumpre_limite: boolean;
}

export interface ApuracaoVAATEducacaoInfantil extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  valor_exigido: string;
  valor_aplicado: string;
  percentual_aplicado: string;
  percentual_vaat_publicado: string | null;
  portaria_vaat_referencia: string;
  cumpre_limite: boolean;
}

export interface ApuracaoVAATDespesaCapital extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  valor_exigido: string;
  valor_aplicado: string;
  percentual_aplicado: string;
  cumpre_limite: boolean;
}

export interface ApuracaoValorNaoAplicadoFundeb extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  valor_maximo_permitido: string;
  valor_nao_aplicado: string;
  valor_nao_aplicado_apos_ajuste: string;
  valor_excedente_ao_maximo_permitido: string;
  percentual_nao_aplicado: string;
  cumpre_limite: boolean;
}

export interface ApuracaoReprogramacaoFundebOrigem {
  id: number;
  origem: "IMPOSTOS" | "UNIAO";
  valor_superavit_permitido_exercicio_anterior: string;
  valor_nao_aplicado_exercicio_anterior: string;
  valor_aplicado_ate_primeiro_quadrimestre: string;
  valor_aplicado_apos_primeiro_quadrimestre: string;
  valor_nao_aplicado_ate_primeiro_quadrimestre_atual: string;
}

export interface ApuracaoReprogramacaoFundeb extends CampoOrigemRegistro {
  id: number;
  municipio: number;
  municipio_nome: string;
  exercicio: number;
  bimestre: number;
  valor_superavit_permitido_exercicio_anterior: string;
  valor_nao_aplicado_exercicio_anterior: string;
  valor_aplicado_ate_primeiro_quadrimestre: string;
  valor_aplicado_apos_primeiro_quadrimestre: string;
  valor_aplicado_ate_primeiro_quadrimestre_empenhado: string;
  valor_aplicado_apos_primeiro_quadrimestre_empenhado: string;
  valor_nao_aplicado_ate_primeiro_quadrimestre_atual: string;
  origens: ApuracaoReprogramacaoFundebOrigem[];
  cumpre_limite: boolean;
}

export type EscopoObrigacao = "MUNICIPIO" | "UNIDADE_GESTORA";

export type PeriodicidadeObrigacao =
  | "MENSAL"
  | "BIMESTRAL"
  | "TRIMESTRAL"
  | "QUADRIMESTRAL"
  | "SEMESTRAL"
  | "ANUAL";

export interface TipoObrigacao {
  id: number;
  nome: string;
  descricao: string;
  orgao_externo: string;
  escopo: EscopoObrigacao;
  periodicidade: PeriodicidadeObrigacao | null;
  prazo_meses_apos_periodo: number | null;
  prazo_dia_limite: number | null;
  ajustar_prazo_para_dia_util: boolean;
  dias_antecedencia_alerta: number;
  url_consulta: string;
  ativo: boolean;
  ordem: number;
  unidades_gestoras_restritas_nomes: string;
}

export interface Obrigacao extends CampoOrigemRegistro {
  id: number;
  tipo_obrigacao: number;
  tipo_obrigacao_nome: string;
  url_consulta: string;
  municipio: number;
  municipio_nome: string;
  unidade_gestora: number | null;
  unidade_gestora_nome: string | null;
  exercicio: number;
  numero_competencia: number;
  rotulo_competencia: string;
  data_fim_periodo: string;
  prazo_limite: string;
  status: "PENDENTE" | "CUMPRIDA";
  situacao: "PENDENTE" | "PROXIMA_DO_PRAZO" | "ATRASADA" | "CUMPRIDA";
  atrasada: boolean;
  proxima_do_prazo: boolean;
  data_cumprimento: string | null;
  protocolo: string;
  observacao: string;
  comprovante: string | null;
  verificado_por: number | null;
  verificado_em: string | null;
}
