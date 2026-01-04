import { apiGet } from "./lib/api";

export default async function Home() {
  let health: any = null;
  let ping: any = null;

  try {
    health = await apiGet("/health");
    ping = await apiGet("/ping");
  } catch (err) {
    console.error("Backend not reachable:", err);
  }

  return (
    <main className="min-h-screen bg-zinc-900 text-white flex flex-col items-center justify-center gap-6">
      <h1 className="text-3xl font-bold">Inbox → Insights MVP</h1>

      <div className="bg-zinc-800 rounded-lg p-4 w-[380px]">
        <h2 className="font-semibold mb-2">Backend Status</h2>

        {health ? (
          <p>Health: ✅ {health.status}</p>
        ) : (
          <p>Health: ❌ Offline</p>
        )}

        {ping ? (
          <p>Ping: 🟢 {ping.message}</p>
        ) : (
          <p>Ping: 🔴 Failed</p>
        )}
      </div>
    </main>
  );
}
