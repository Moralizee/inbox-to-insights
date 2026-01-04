"use client";

import { useEffect, useState } from "react";

interface Email {
  id: number;
  subject: string;

  from_name: string | null;
  from_email: string | null;

  sender_domain: string;
  provider: string;

  category: string;
  intent: string;

  risk_score: number;
  is_noreply: boolean;

  // NEW reply-intelligence fields (list endpoint)
  requires_reply?: boolean;
  action_request?: boolean;
  urgency?: string;
  reply_score?: number;

  preview: string;
}

interface EmailLink {
  url: string;
  domain: string;
}

interface EmailDetail extends Email {
  from_raw: string;
  body: string;

  risk_flags?: string[];

  // NEW detail-view reply fields
  assigned_to_user?: string | null;
  reply_flags?: string[];

  links: EmailLink[];
}

export default function EmailsDashboard() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedEmail, setSelectedEmail] =
    useState<EmailDetail | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [filters, setFilters] = useState({
    q: "",
    category: "",
    intent: "",
    min_risk: 0,
    max_risk: 1,
  });

  // ---------- Load email list ----------
  async function loadEmails() {
    setLoading(true);

    const params = new URLSearchParams();

    if (filters.q) params.append("q", filters.q);
    if (filters.category) params.append("category", filters.category);
    if (filters.intent) params.append("intent", filters.intent);

    params.append("min_risk", String(filters.min_risk));
    params.append("max_risk", String(filters.max_risk));

    const res = await fetch(
      `http://127.0.0.1:8000/emails?${params.toString()}`
    );

    const data: Email[] = await res.json();
    setEmails(data);
    setLoading(false);
  }

  useEffect(() => {
    loadEmails();
  }, [filters]);

  // ---------- Load inspector panel ----------
  async function openEmail(id: number) {
    // clicking same row -> do nothing
    if (selectedEmail?.id === id) return;

    setSelectedId(id);
    setLoadingDetail(true);

    const res = await fetch(`http://127.0.0.1:8000/emails/${id}`);
    const data: EmailDetail = await res.json();

    setSelectedEmail(data);
    setLoadingDetail(false);
  }

  // ---------- Keyboard navigation (↑ ↓ Enter) ----------
  useEffect(() => {
    function handleKeys(e: KeyboardEvent) {
      if (!emails.length) return;

      const currentIndex = selectedId
        ? emails.findIndex((em) => em.id === selectedId)
        : -1;

      // ↓ NEXT
      if (e.key === "ArrowDown") {
        e.preventDefault();
        const next = Math.min(currentIndex + 1, emails.length - 1);
        const email = emails[next];
        setSelectedId(email.id);
        openEmail(email.id);
      }

      // ↑ PREV
      if (e.key === "ArrowUp") {
        e.preventDefault();
        const prev = Math.max(currentIndex - 1, 0);
        const email = emails[prev];
        setSelectedId(email.id);
        openEmail(email.id);
      }

      // ENTER → reopen if closed
      if (e.key === "Enter" && selectedId) {
        openEmail(selectedId);
      }
    }

    window.addEventListener("keydown", handleKeys);
    return () => window.removeEventListener("keydown", handleKeys);
  }, [emails, selectedId, selectedEmail]);

  function urgencyBadge(level?: string) {
    if (!level || level === "none") return null;

    const style =
      level === "high"
        ? "bg-red-500/30 text-red-300"
        : level === "medium"
        ? "bg-amber-500/30 text-amber-300"
        : "bg-green-500/30 text-green-300";

    return (
      <span className={`ml-2 px-2 py-1 rounded ${style}`}>
        ⏳ {level}
      </span>
    );
  }

  // ---------- Safe flag arrays for the detail panel ----------
  const replyFlags = selectedEmail?.reply_flags ?? [];
  const riskFlags = selectedEmail?.risk_flags ?? [];

  return (
    <div className="h-screen bg-zinc-950 text-white flex">
      {/* ================= LEFT: DASHBOARD ================= */}
      <div className="flex-1 p-6 flex flex-col items-center">
        <h1 className="text-2xl font-semibold mb-4">
          Inbox Insights Dashboard
        </h1>

        <div className="w-[1100px]">
          {/* Filters */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            <input
              className="px-3 py-2 rounded bg-zinc-900 border border-zinc-700"
              placeholder="Search subject or preview…"
              value={filters.q}
              onChange={(e) =>
                setFilters((f) => ({ ...f, q: e.target.value }))
              }
            />

            <select
              className="px-3 py-2 rounded bg-zinc-900 border border-zinc-700"
              value={filters.category}
              onChange={(e) =>
                setFilters((f) => ({ ...f, category: e.target.value }))
              }
            >
              <option value="">All categories</option>
              <option value="security_alert">Security Alerts</option>
              <option value="billing">Billing</option>
              <option value="newsletter">Newsletters</option>
              <option value="promotion">Promotions</option>
            </select>

            <select
              className="px-3 py-2 rounded bg-zinc-900 border border-zinc-700"
              value={filters.intent}
              onChange={(e) =>
                setFilters((f) => ({ ...f, intent: e.target.value }))
              }
            >
              <option value="">All intents</option>
              <option value="login_security_notice">
                Login / Security
              </option>
              <option value="transaction_notification">
                Transactions
              </option>
              <option value="content_digest">Content Digest</option>
              <option value="marketing_offer">Marketing Offer</option>
            </select>

            <select
              className="px-3 py-2 rounded bg-zinc-900 border border-zinc-700"
              onChange={(e) => {
                const v = e.target.value;
                if (v === "high")
                  setFilters((f) => ({ ...f, min_risk: 0.5, max_risk: 1 }));
                else if (v === "medium")
                  setFilters((f) => ({ ...f, min_risk: 0.2, max_risk: 0.5 }));
                else if (v === "low")
                  setFilters((f) => ({ ...f, min_risk: 0, max_risk: 0.2 }));
                else
                  setFilters((f) => ({ ...f, min_risk: 0, max_risk: 1 }));
              }}
            >
              <option value="">All risk levels</option>
              <option value="high">High risk</option>
              <option value="medium">Medium risk</option>
              <option value="low">Low risk</option>
            </select>
          </div>

          {/* Table */}
          <div className="border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-900 border-b border-zinc-800">
                <tr>
                  <th className="px-3 py-2 text-left">Category</th>
                  <th className="px-3 py-2 text-left">Risk</th>
                  <th className="px-3 py-2 text-left">From</th>
                  <th className="px-3 py-2 text-left">Intent</th>
                  <th className="px-3 py-2 text-left">Subject</th>
                </tr>
              </thead>

              <tbody>
                {loading && (
                  <tr>
                    <td className="px-3 py-4" colSpan={6}>
                      Loading…
                    </td>
                  </tr>
                )}

                {!loading &&
                  emails.map((email) => (
                    <tr
                      key={email.id}
                      onClick={() => openEmail(email.id)}
                      className={`
                        border-b border-zinc-800 cursor-pointer
                        hover:bg-zinc-900
                        ${selectedId === email.id ? "bg-zinc-800/70" : ""}
                      `}
                    >
                      <td className="px-3 py-2">
                        <span className="px-2 py-1 bg-zinc-800 rounded">
                          {email.category}
                        </span>
                      </td>

                      <td className="px-3 py-2 font-mono">
                        {email.risk_score.toFixed(2)}
                      </td>

                      <td className="px-3 py-2">
                        {email.from_email ?? "(unknown)"}
                      </td>

                      <td className="px-3 py-2">
                        <span className="px-2 py-1 bg-zinc-800 rounded">
                          {email.intent}
                        </span>

                        {email.requires_reply && (
                          <span className="ml-2 px-2 py-1 rounded bg-blue-500/30 text-blue-300">
                            📬 Reply
                          </span>
                        )}

                        {email.action_request && (
                          <span className="ml-2 px-2 py-1 rounded bg-amber-500/30 text-amber-300">
                            🛠 Action
                          </span>
                        )}

                        {urgencyBadge(email.urgency)}
                      </td>

                      <td className="px-3 py-2 truncate max-w-sm">
                        {email.subject}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ================= RIGHT: FIXED PANEL ================= */}
      <div className="w-[480px] border-l border-zinc-800 bg-zinc-900 p-4 overflow-y-auto">
        {!selectedEmail && (
          <div className="opacity-60 text-sm">
            📨 Select an email from the list to view details
          </div>
        )}

        {selectedEmail && (
          <>
            <button
              className="mb-3 px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700"
              onClick={() => setSelectedEmail(null)}
            >
              Close
            </button>

            {loadingDetail ? (
              <p>Loading…</p>
            ) : (
              <div className="space-y-3">
                <h2 className="text-lg font-semibold">
                  {selectedEmail.subject}
                </h2>

                <div className="text-sm opacity-80">
                  From: {selectedEmail.from_name ?? "(Unknown)"}{" "}
                  &lt;{selectedEmail.from_email}&gt;
                </div>

                <div className="text-sm">
                  <b>Domain:</b> {selectedEmail.sender_domain}
                </div>

                <div className="text-sm">
                  <b>Provider:</b> {selectedEmail.provider}
                </div>

                {selectedEmail.is_noreply && (
                  <p className="text-amber-300 text-sm">
                    ⚠️ System no-reply sender
                  </p>
                )}

                <div className="flex gap-2 text-sm pt-1">
                  <span className="px-2 py-1 bg-zinc-800 rounded">
                    🏷 {selectedEmail.category}
                  </span>

                  <span className="px-2 py-1 bg-zinc-800 rounded">
                    🎯 {selectedEmail.intent}
                  </span>
                </div>

                {/* Reply Intelligence */}
                <div className="flex gap-2 text-sm">
                  {selectedEmail.requires_reply && (
                    <span className="px-2 py-1 rounded bg-blue-500/30 text-blue-300">
                      📬 Reply Expected
                    </span>
                  )}

                  {selectedEmail.action_request && (
                    <span className="px-2 py-1 rounded bg-amber-500/30 text-amber-300">
                      🛠 Action Requested
                    </span>
                  )}

                  {selectedEmail.assigned_to_user && (
                    <span className="px-2 py-1 rounded bg-purple-500/30 text-purple-300">
                      👤 Assigned to You
                    </span>
                  )}

                  {urgencyBadge(selectedEmail.urgency)}
                </div>

                {selectedEmail.reply_score !== undefined && (
                  <p className="text-sm opacity-80">
                    Reply confidence score:{" "}
                    <b>{selectedEmail.reply_score}</b>
                  </p>
                )}

                {replyFlags.length > 0 && (
                  <ul className="list-disc ml-4 text-blue-300 text-sm">
                    {replyFlags.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                )}

                <p className="font-semibold">
                  Risk Score: {selectedEmail.risk_score.toFixed(2)}
                </p>

                {riskFlags.length > 0 && (
                  <ul className="list-disc ml-4 text-amber-300 text-sm">
                    {riskFlags.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                )}

                {selectedEmail.links?.length > 0 && (
                  <div className="pt-2 text-sm">
                    <b>Links detected:</b>
                    <ul className="mt-1 space-y-1">
                      {selectedEmail.links.map((l, i) => (
                        <li key={i} className="truncate">
                          🔗{" "}
                          <a
                            href={l.url}
                            target="_blank"
                            className="text-blue-300 underline"
                          >
                            {l.url}
                          </a>{" "}
                          <span className="opacity-70">
                            ({l.domain})
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="pt-2">
                  <b>Preview:</b>
                  <p className="opacity-80 text-sm">
                    {selectedEmail.preview}
                  </p>
                </div>

                <details className="pt-2">
                  <summary className="cursor-pointer">
                    View full body
                  </summary>
                  <pre className="mt-1 whitespace-pre-wrap text-sm opacity-80">
                    {selectedEmail.body}
                  </pre>
                </details>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
