import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function ClassificacaoReceitaAlineasPage() {
  const [opcoesRubrica, setOpcoesRubrica] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    api.get("/classificacao-receita-rubricas/", { params: { page_size: 500 } }).then(({ data }) => {
      setOpcoesRubrica(
        (data.results ?? data).map((r: { id: number; especie_codigo: string; codigo: string; nome: string }) => ({
          value: r.id,
          label: `${r.especie_codigo}.${r.codigo} - ${r.nome}`,
        }))
      );
    });
  }, []);

  return (
    <CrudManager
      titulo="Receita — Alíneas (nível 5)"
      recurso="classificacao-receita-alineas"
      campos={[
        { chave: "rubrica", rotulo: "Rubrica (STN)", tipo: "select", opcoes: opcoesRubrica, obrigatorio: true },
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
      dependenciasRecarregar={[opcoesRubrica.length]}
    />
  );
}
