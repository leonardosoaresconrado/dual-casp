import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function ClassificacaoReceitaOrigensPage() {
  const [opcoesCategoria, setOpcoesCategoria] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    // Categoria Econômica é compartilhada com a despesa (mesmo catálogo
    // nacional — ver CategoriasEconomicasPage.tsx); aqui só os códigos "1"
    // (Receitas Correntes) e "2" (Receitas de Capital) fazem sentido como
    // nível 1 da receita, por isso o filtro client-side.
    api.get("/categorias-economicas/", { params: { page_size: 500 } }).then(({ data }) => {
      setOpcoesCategoria(
        (data.results ?? data)
          .filter((c: { codigo: string }) => c.codigo === "1" || c.codigo === "2")
          .map((c: { id: number; codigo: string; nome: string }) => ({
            value: c.id,
            label: `${c.codigo} - ${c.nome}`,
          }))
      );
    });
  }, []);

  return (
    <CrudManager
      titulo="Receita — Origens (nível 2)"
      recurso="classificacao-receita-origens"
      campos={[
        { chave: "categoria", rotulo: "Categoria Econômica", tipo: "select", opcoes: opcoesCategoria, obrigatorio: true },
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
      dependenciasRecarregar={[opcoesCategoria.length]}
    />
  );
}
