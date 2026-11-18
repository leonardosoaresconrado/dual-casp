import { CrudManager } from "../../components/CrudManager";

export function FontesRecursosPage() {
  return (
    <CrudManager
      titulo="Fontes de Recursos"
      recurso="fontes-recursos"
      campos={[
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        // Derivada do 1º dígito do código (ver FonteRecursos.natureza no
        // backend) — só exibição, nunca editável diretamente.
        { chave: "natureza_label", rotulo: "Natureza", somenteColuna: true },
      ]}
    />
  );
}
