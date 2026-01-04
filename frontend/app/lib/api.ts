export async function apiGet(path: string) {
  const res = await fetch(`http://localhost:8000${path}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Backend request failed");
  }

  return res.json();
}
