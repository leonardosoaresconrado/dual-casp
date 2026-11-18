import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

const OPCOES_NATUREZA: OpcaoCampo[] = [
  { value: "CORRENTE", label: "Corrente" },
  { value: "CAPITAL", label: "Capital" },
];

export function CategoriasEconomicasPage() {
  return (
    <CrudManager
      titulo="Categorias Econômicas (Receita e Despesa)"
      recurso="categorias-economicas"
      campos={[
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        { chave: "natureza", rotulo: "Natureza", tipo: "select", opcoes: OPCOES_NATUREZA },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
    />
  );
}
