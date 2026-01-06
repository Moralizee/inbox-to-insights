const API_BASE = "http://127.0.0.1:8000";

export async function apiGet(path: string) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`API request failed: ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    console.error(`GET ${path} failed`, err);
    throw err;
  }
}