import { apiUrl } from "./url";

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  resourceName = "API",
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const response = await fetch(apiUrl(
    path, import.meta.env?.VITE_API_BASE_URL, import.meta.env?.PROD ?? false,
  ), {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `${resourceName} request failed with status ${response.status}.`;

    try {
      const errorData: unknown = await response.json();

      if (typeof errorData === "object" && errorData !== null && "detail" in errorData) {
        const detail = errorData.detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (detail != null) {
          message = JSON.stringify(detail);
        }
      }
    } catch {
      // Keep the HTTP status message when the error response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}
