import type { CampoFormulario, OpcaoCampo } from "../../components/CrudManager";

const OPCOES_ORIGEM: OpcaoCampo[] = [
  { value: "OFICIAL", label: "Oficial (STN/SOF)" },
  { value: "MUNICIPAL", label: "Municipal" },
];

export const CAMPOS_CLASSIFICACAO_OFICIAL: CampoFormulario[] = [
  { chave: "origem_classificacao", rotulo: "Origem", tipo: "select", opcoes: OPCOES_ORIGEM },
  { chave: "ano_vigencia_inicial", rotulo: "Vigente desde (ano)", tipo: "numero" },
  { chave: "ativo", rotulo: "Ativo", tipo: "booleano" },
];

export const VALORES_PADRAO_CLASSIFICACAO_OFICIAL = { ativo: true, origem_classificacao: "OFICIAL" };
