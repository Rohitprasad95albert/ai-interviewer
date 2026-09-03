/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * NEXT_PUBLIC_API_URL is inlined into the browser bundle at build time (see
 * Next.js env var docs), so it's safe to reference on the client - it must
 * never hold a secret, only the backend's public base URL.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: "ok" | "degraded";
  environment: string;
  database: "connected" | "unavailable";
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json();
}

export { API_BASE_URL };
