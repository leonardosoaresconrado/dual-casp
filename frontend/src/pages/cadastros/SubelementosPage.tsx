import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { CAMPOS_CLASSIFICACAO_OFICIAL, VALORES_PADRAO_CLASSIFICACAO_OFICIAL } from "./camposClassificacaoOficial";

export function SubelementosPage() {
  const [opcoesElemento, setOpcoesElemento] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    api.get("/elementos-despesa/", { params: { page_size: 500 } }).then(({ data }) => {
      setOpcoesElemento(
        (data.results ?? data).map((e: { id: number; codigo: string; nome: string }) => ({
          value: e.id,
          label: `${e.codigo} - ${e.nome}`,
        }))
      );
    });
  }, []);

  return (
    <CrudManager
      titulo="Subelementos de Despesa"
      recurso="subelementos"
      campos={[
        { chave: "elemento", rotulo: "Elemento de Despesa", tipo: "select", opcoes: opcoesElemento, obrigatorio: true },
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        ...CAMPOS_CLASSIFICACAO_OFICIAL,
      ]}
      valoresPadrao={VALORES_PADRAO_CLASSIFICACAO_OFICIAL}
      dependenciasRecarregar={[opcoesElemento.length]}
    />
  );
}
