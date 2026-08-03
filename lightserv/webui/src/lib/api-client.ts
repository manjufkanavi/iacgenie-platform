const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3071";

export interface ApiOptions {
  apiKey?: string;
}

async function request<T>(
  endpoint: string,
  options: RequestInit & ApiOptions = {}
): Promise<T> {
  const { apiKey, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...fetchOptions,
    headers: { ...headers, ...(fetchOptions.headers as Record<string, string>) },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Request failed" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  search: (params: { query: string }) =>
    request("/search", { method: "POST", body: JSON.stringify(params) }),
  scrape: (params: { url: string }) =>
    request("/scrape", { method: "POST", body: JSON.stringify(params) }),
  createKey: () =>
    request<{ key: { id: string; key: string } }>(`/keys`, {
      method: "POST",
    }),
  listKeys: () =>
    request<{ keys: any[] }>(`/keys`),
  revokeKey: (id: string) =>
    request(`/keys/${id}`, { method: "DELETE" }),
};
