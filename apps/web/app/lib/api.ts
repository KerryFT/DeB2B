export const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

function csrfToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const entry = document.cookie.split("; ").find((item) => item.startsWith("deb2b_csrf="));
  return entry ? decodeURIComponent(entry.split("=").slice(1).join("=")) : undefined;
}

export function apiHeaders(role?: string, json = false): Record<string, string> {
  const headers: Record<string, string> = json ? { "content-type": "application/json" } : {};
  const csrf = csrfToken();
  if (csrf) headers["x-csrf-token"] = csrf;
  if (process.env.NEXT_PUBLIC_DEV_AUTH_ENABLED !== "true") return headers;
  const userId = process.env.NEXT_PUBLIC_DEV_USER_ID;
  const tenantId = process.env.NEXT_PUBLIC_DEV_TENANT_ID;
  if (!userId || !tenantId) throw new Error("local dev auth IDs are not configured");
  headers["x-dev-user-id"] = userId;
  headers["x-dev-tenant-id"] = tenantId;
  if (role) headers["x-dev-role"] = role;
  return headers;
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const csrf = csrfToken();
  if (csrf && !headers.has("x-csrf-token")) headers.set("x-csrf-token", csrf);
  return fetch(`${apiBase}${path}`, { ...init, headers, credentials: "include" });
}
