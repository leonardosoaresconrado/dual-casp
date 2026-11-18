import { CrudManager } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function GruposNaturezaDespesaPage() {
  return (
    <CrudManager
      titulo="Grupos de Natureza de Despesa"
      recurso="grupos-natureza-despesa"
      campos={[
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
    />
  );
}
