import { CrudManager } from "../../components/CrudManager";

export function SubfuncoesPage() {
  return (
    <CrudManager
      titulo="Subfunções"
      recurso="subfuncoes"
      campos={[
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
      ]}
    />
  );
}
