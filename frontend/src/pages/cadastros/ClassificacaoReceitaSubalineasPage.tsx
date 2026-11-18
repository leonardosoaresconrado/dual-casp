import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function ClassificacaoReceitaSubalineasPage() {
  const [opcoesAlinea, setOpcoesAlinea] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    api.get("/classificacao-receita-alineas/", { params: { page_size: 500 } }).then(({ data }) => {
      setOpcoesAlinea(
        (data.results ?? data).map((a: { id: number; rubrica_codigo: string; codigo: string; nome: string }) => ({
          value: a.id,
          label: `${a.rubrica_codigo}.${a.codigo} - ${a.nome}`,
        }))
      );
    });
  }, []);

  return (
    <CrudManager
      titulo="Receita — Subalíneas (nível 6)"
      recurso="classificacao-receita-subalineas"
      campos={[
        { chave: "alinea", rotulo: "Alínea", tipo: "select", opcoes: opcoesAlinea, obrigatorio: true },
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
      dependenciasRecarregar={[opcoesAlinea.length]}
    />
  );
}
