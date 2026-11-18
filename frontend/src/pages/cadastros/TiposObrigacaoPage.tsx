import { CrudManager } from "../../components/CrudManager";

const OPCOES_ESCOPO = [
  { value: "MUNICIPIO", label: "Município (todo o município)" },
  { value: "UNIDADE_GESTORA", label: "Unidade Gestora" },
];

const OPCOES_PERIODICIDADE = [
  { value: "MENSAL", label: "Mensal" },
  { value: "BIMESTRAL", label: "Bimestral" },
  { value: "TRIMESTRAL", label: "Trimestral" },
  { value: "QUADRIMESTRAL", label: "Quadrimestral" },
  { value: "SEMESTRAL", label: "Semestral" },
  { value: "ANUAL", label: "Anual" },
];

export function TiposObrigacaoPage() {
  return (
    <CrudManager
      titulo="Tipos de Obrigação (Consultas Públicas)"
      recurso="tipos-obrigacao"
      campos={[
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        { chave: "orgao_externo", rotulo: "Órgão Externo" },
        { chave: "escopo", rotulo: "Escopo", tipo: "select", opcoes: OPCOES_ESCOPO, obrigatorio: true },
        {
          chave: "periodicidade",
          rotulo: "Periodicidade (deixe vazio até confirmar a regra oficial)",
          tipo: "select",
          opcoes: OPCOES_PERIODICIDADE,
        },
        { chave: "prazo_meses_apos_periodo", rotulo: "Prazo — meses após o período", tipo: "numero" },
        { chave: "prazo_dia_limite", rotulo: "Prazo — dia-limite do mês (1-31)", tipo: "numero" },
        { chave: "ajustar_prazo_para_dia_util", rotulo: "Ajustar p/ dia útil se cair em fim de semana", tipo: "booleano" },
        { chave: "dias_antecedencia_alerta", rotulo: "Dias de antecedência p/ alerta", tipo: "numero" },
        { chave: "url_consulta", rotulo: "URL de Consulta Pública" },
        { chave: "ordem", rotulo: "Ordem", tipo: "numero" },
        { chave: "unidades_gestoras_restritas_nomes", rotulo: "Restrito a (UGs)", somenteColuna: true },
        { chave: "descricao", rotulo: "Descrição", tipo: "textarea" },
        { chave: "ativo", rotulo: "Ativo", tipo: "booleano" },
      ]}
      valoresPadrao={{ escopo: "MUNICIPIO", ativo: true, dias_antecedencia_alerta: 10 }}
    />
  );
}
