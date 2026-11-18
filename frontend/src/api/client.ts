import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refrescando: Promise<string | null> | null = null;

async function renovarToken(): Promise<string | null> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${API_URL}/auth/refresh/`, { refresh });
    localStorage.setItem("access_token", data.access);
    return data.access as string;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      refrescando = refrescando ?? renovarToken();
      const novoToken = await refrescando;
      refrescando = null;
      if (novoToken) {
        originalRequest.headers.Authorization = `Bearer ${novoToken}`;
        return api(originalRequest);
      }
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// O backend limita page_size a 2000 (PaginacaoPadrao.max_page_size) — um
// page_size maior que isso trunca silenciosamente em vez de dar erro.
// Percorre as páginas (via o `next` do DRF) até esgotar o resultado.
export async function buscarTodasPaginas<T>(url: string, params: Record<string, unknown>): Promise<T[]> {
  const resultados: T[] = [];
  let proximaUrl: string | null = url;
  let proximosParams: Record<string, unknown> | undefined = { ...params, page_size: 2000 };
  while (proximaUrl) {
    const { data }: { data: { results: T[]; next: string | null } } = await api.get<{
      results: T[];
      next: string | null;
    }>(proximaUrl, {
      params: proximosParams,
    });
    resultados.push(...data.results);
    proximaUrl = data.next;
    proximosParams = undefined;
  }
  return resultados;
}

// Usado para pré-selecionar automaticamente "o último mês com movimento"
// em páginas que buscam LancamentoExecucaoOrcamentaria já filtrado por mês
// (não dá pra descobrir isso client-side sem antes buscar o mês certo).
// Reusa `/execucao-orcamentaria/tendencia/`, que já agrupa por
// mes_referencia — GROUP BY só traz meses com pelo menos uma linha, então
// o maior valor retornado é exatamente "o último mês com empenho".
export async function buscarUltimoMesComMovimento(loaId: number): Promise<number | null> {
  const { data } = await api.get<{ mes_referencia: number }[]>("/execucao-orcamentaria/tendencia/", {
    params: { loa: loaId },
  });
  if (data.length === 0) return null;
  return Math.max(...data.map((d) => d.mes_referencia));
}
