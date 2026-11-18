import { CrudManager } from "../../components/CrudManager";

export function FuncoesPage() {
  return (
    <CrudManager
      titulo="Funções"
      recurso="funcoes"
      campos={[
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
      ]}
    />
  );
}
