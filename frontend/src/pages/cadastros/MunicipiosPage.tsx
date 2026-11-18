import { CrudManager } from "../../components/CrudManager";

export function MunicipiosPage() {
  return (
    <CrudManager
      titulo="Municípios"
      recurso="municipios"
      campos={[
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        { chave: "uf", rotulo: "UF", obrigatorio: true },
        { chave: "codigo_ibge", rotulo: "Código IBGE", obrigatorio: true },
        { chave: "ativo", rotulo: "Ativo", tipo: "booleano" },
      ]}
      valoresPadrao={{ ativo: true }}
    />
  );
}
