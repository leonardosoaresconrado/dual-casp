import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function ClassificacaoReceitaRubricasPage() {
  const [opcoesEspecie, setOpcoesEspecie] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    api.get("/classificacao-receita-especies/", { params: { page_size: 500 } }).then(({ data }) => {
      setOpcoesEspecie(
        (data.results ?? data).map((e: { id: number; origem_codigo: string; codigo: string; nome: string }) => ({
          value: e.id,
          label: `${e.origem_codigo}.${e.codigo} - ${e.nome}`,
        }))
      );
    });
  }, []);

  return (
    <CrudManager
      titulo="Receita — Rubricas STN (nível 4)"
      recurso="classificacao-receita-rubricas"
      campos={[
        { chave: "especie", rotulo: "Espécie", tipo: "select", opcoes: opcoesEspecie, obrigatorio: true },
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
      dependenciasRecarregar={[opcoesEspecie.length]}
    />
  );
}
