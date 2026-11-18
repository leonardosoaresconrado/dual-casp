import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function ClassificacaoReceitaTiposPage() {
  const [opcoesSubalinea, setOpcoesSubalinea] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    api.get("/classificacao-receita-subalineas/", { params: { page_size: 500 } }).then(({ data }) => {
      setOpcoesSubalinea(
        (data.results ?? data).map((s: { id: number; alinea_codigo: string; codigo: string; nome: string }) => ({
          value: s.id,
          label: `${s.alinea_codigo}.${s.codigo} - ${s.nome}`,
        }))
      );
    });
  }, []);

  return (
    <CrudManager
      titulo="Receita — Tipos (nível 7)"
      recurso="classificacao-receita-tipos"
      campos={[
        { chave: "subalinea", rotulo: "Subalínea", tipo: "select", opcoes: opcoesSubalinea, obrigatorio: true },
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
      dependenciasRecarregar={[opcoesSubalinea.length]}
    />
  );
}
