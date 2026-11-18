import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function ClassificacaoReceitaEspeciesPage() {
  const [opcoesOrigem, setOpcoesOrigem] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    api.get("/classificacao-receita-origens/", { params: { page_size: 500 } }).then(({ data }) => {
      setOpcoesOrigem(
        (data.results ?? data).map((o: { id: number; categoria_codigo: string; codigo: string; nome: string }) => ({
          value: o.id,
          label: `${o.categoria_codigo}.${o.codigo} - ${o.nome}`,
        }))
      );
    });
  }, []);

  return (
    <CrudManager
      titulo="Receita — Espécies (nível 3)"
      recurso="classificacao-receita-especies"
      campos={[
        { chave: "origem", rotulo: "Origem", tipo: "select", opcoes: opcoesOrigem, obrigatorio: true },
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
      dependenciasRecarregar={[opcoesOrigem.length]}
    />
  );
}
