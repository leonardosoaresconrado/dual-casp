import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Parametro } from "../api/types";
import { useAuth } from "../auth/AuthContext";

interface ParametrosContextValue {
  // chave -> valor_booleano. Vazio enquanto carrega — `useParametro` cobre
  // isso com um valor padrão, nunca esconde conteúdo antes do fetch resolver.
  valores: Record<string, boolean>;
  recarregar: () => void;
}

const ParametrosContext = createContext<ParametrosContextValue | undefined>(undefined);

// Carregado uma vez por sessão (não por-município, ao contrário de
// ScopeContext) — os parâmetros em Administração > Parâmetros afetam a
// interface igualmente pra todo mundo autenticado.
export function ParametrosProvider({ children }: { children: ReactNode }) {
  const { usuario } = useAuth();
  const [valores, setValores] = useState<Record<string, boolean>>({});

  function carregar() {
    api.get<{ results: Parametro[] }>("/parametros/").then(({ data }) => {
      setValores(Object.fromEntries(data.results.map((p) => [p.chave, p.valor_booleano])));
    });
  }

  useEffect(() => {
    if (!usuario) return;
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usuario]);

  return (
    <ParametrosContext.Provider value={{ valores, recarregar: carregar }}>{children}</ParametrosContext.Provider>
  );
}

export function useParametros() {
  const ctx = useContext(ParametrosContext);
  if (!ctx) throw new Error("useParametros deve ser usado dentro de ParametrosProvider");
  return ctx;
}

// Lê um parâmetro booleano por chave — `padrao` cobre tanto o fetch ainda
// não ter resolvido quanto uma chave desconhecida, sempre do lado "mostrar"
// (nunca esconder conteúdo por um parâmetro ainda não carregado).
export function useParametro(chave: string, padrao = true): boolean {
  const { valores } = useParametros();
  return valores[chave] ?? padrao;
}
