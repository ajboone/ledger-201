/** Existing resource paths include /api; an override may be an origin or API base. */
export function apiUrl(
  path: string,
  configuredBase: string | undefined,
  production: boolean,
): string {
  const base = (configuredBase ?? (production ? "/api" : "http://127.0.0.1:8000"))
    .replace(/\/+$/, "");
  const resource = base.endsWith("/api") && (path === "/api" || path.startsWith("/api/"))
    ? path.slice(4)
    : path;
  return `${base}${resource}`;
}
