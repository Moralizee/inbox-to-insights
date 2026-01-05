"use client";

import { useEffect, useState } from "react";

const currentUser = {
  name: "N Analyst",
  email: "analyst@corp.local",
};

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
  preview: string;

  requires_reply?: boolean;
  reply_score?: number;

  status?: "open" | "in_review" | "resolved";
  assignee_name?: string;
  assignee_email?: string;
}

interface EmailLink {
  url: string;
  domain: string;
}

interface EmailDetail extends Email {
  from_raw: string;
  body: string;

  links: EmailLink[];

  risk_flags?: string[];
  reply_flags?: string[];

  action_request?: boolean;
  urgency?: string;
  assigned_at?: string | null;
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
    suspicious_only: false,
  });

  async function loadEmails() {
    setLoading(true);

    const params = new URLSearchParams();

    if (filters.q) params.append("q", filters.q);
    if (filters.category) params.append("category", filters.category);
    if (filters.intent) params.append("intent", filters.intent);
    if (filters.suspicious_only)
      params.append("suspicious_only", "true");

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

  async function openEmail(id: number) {
    if (selectedEmail?.id === id) return;

    setSelectedId(id);
    setLoadingDetail(true);

    const res = await fetch(`http://127.0.0.1:8000/emails/${id}`);
    const data: EmailDetail = await res.json();

    setSelectedEmail(data);
    setLoadingDetail(false);
  }

  async function assignEmail(id: number) {
    await fetch(`http://127.0.0.1:8000/emails/${id}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        assignee_name: currentUser.name,
        assignee_email: currentUser.email,
      }),
    });

    setSelectedEmail(prev =>
      prev
        ? {
            ...prev,
            status: "in_review",
            assignee_name: currentUser.name,
            assignee_email: currentUser.email,
          }
        : prev
    );

    setEmails(list =>
      list.map(e =>
        e.id === id
          ? {
              ...e,
              status: "in_review",
              assignee_name: currentUser.name,
              assignee_email: currentUser.email,
            }
          : e
      )
    );
  }

  async function unassignEmail(id: number) {
    await fetch(`http://127.0.0.1:8000/emails/${id}/unassign`, {
      method: "POST",
    });

    setSelectedEmail(prev =>
      prev
        ? {
            ...prev,
            status: "open",
            assignee_name: "",
            assignee_email: "",
          }
        : prev
    );

    setEmails(list =>
      list.map(e =>
        e.id === id
          ? {
              ...e,
              status: "open",
              assignee_name: "",
              assignee_email: "",
            }
          : e
      )
    );
  }

  async function resolveEmail(id: number) {
    await fetch(`http://127.0.0.1:8000/emails/${id}/resolve`, {
      method: "POST",
    });

    setSelectedEmail(prev =>
      prev ? { ...prev, status: "resolved" } : prev
    );

    setEmails(list =>
      list.map(e =>
        e.id === id ? { ...e, status: "resolved" } : e
      )
    );
  }

  const riskFlags = selectedEmail?.risk_flags ?? [];
  const replyFlags = selectedEmail?.reply_flags ?? [];

  function assignedChip(email: Email) {
    if (email.status === "resolved")
      return (
        <span className="px-2 py-0.5 rounded bg-green-500/20 text-green-300">
          Resolved
        </span>
      );

    if (email.status === "in_review")
      return (
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-purple-400" />
          <span className="text-purple-300">
            {email.assignee_name || "Assigned"}
          </span>
        </span>
      );

    return (
      <span className="flex items-center gap-1 opacity-70">
        <span className="w-2 h-2 rounded-full bg-zinc-500" />
        <span>Unassigned</span>
      </span>
    );
  }

  function riskColor(score: number) {
    if (score >= 0.6) return "text-red-400";
    if (score >= 0.3) return "text-amber-300";
    return "text-green-400";
  }

  return (
    <div className="h-screen bg-zinc-950 text-white flex overflow-hidden">

      {/* LEFT: header + filters */}
      <div className="flex-1 flex flex-col">

        <div className="p-6 pb-3">
          <h1 className="text-2xl font-semibold mb-4">
            Inbox Insights Dashboard
          </h1>

          <div className="w-[1100px] space-y-3 mx-auto">
            <div className="flex gap-2">

              <input
                placeholder="Search subject or preview…"
                value={filters.q}
                onChange={e =>
                  setFilters({ ...filters, q: e.target.value })
                }
                className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 w-[280px]"
              />

              <select
                value={filters.category}
                onChange={e =>
                  setFilters({ ...filters, category: e.target.value })
                }
                className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700"
              >
                <option value="">All categories</option>
                <option value="security_alert">Security</option>
                <option value="billing">Billing</option>
                <option value="newsletter">Newsletter</option>
                <option value="promotion">Promotion</option>
                <option value="notification">Notification</option>
              </select>

              <select
                value={filters.intent}
                onChange={e =>
                  setFilters({ ...filters, intent: e.target.value })
                }
                className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700"
              >
                <option value="">All intents</option>
                <option value="login_security_notice">
                  Login alert
                </option>
                <option value="account_access_granted">
                  Access granted
                </option>
                <option value="transaction_notification">
                  Billing notice
                </option>
                <option value="marketing_offer">
                  Marketing
                </option>
                <option value="content_digest">
                  Digest
                </option>
              </select>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={filters.suspicious_only}
                  onChange={e =>
                    setFilters({
                      ...filters,
                      suspicious_only: e.target.checked,
                    })
                  }
                />
                Suspicious only
              </label>
            </div>
          </div>
        </div>

        {/* TABLE + PANEL layout (aligned top edges) */}
        <div className="flex-1 overflow-y-auto px-6 pb-4">

          <div className="flex gap-4 justify-center">

            {/* EMAIL TABLE */}
            <div className="w-[1100px] border border-zinc-800 rounded-xl overflow-hidden">
              <table className="w-full text-sm">

                <thead className="bg-zinc-900/60 border-b border-zinc-800 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2 text-left">Category</th>
                    <th className="px-3 py-2 text-left w-[160px]">Assigned</th>
                    <th className="px-3 py-2 text-left">Risk</th>
                    <th className="px-3 py-2 text-left">Sender</th>
                    <th className="px-3 py-2 text-left">Intent</th>
                    <th className="px-3 py-2 text-left">Subject</th>
                  </tr>
                </thead>

                <tbody>
                  {!loading &&
                    emails.map(email => (
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

                        <td className="px-3 py-2">
                          {assignedChip(email)}
                        </td>

                        <td className="px-3 py-2 font-mono">
                          <span className={riskColor(email.risk_score)}>
                            {email.risk_score.toFixed(2)}
                          </span>
                        </td>

                        <td className="px-3 py-2">
                          {email.from_email ?? "(unknown)"}
                        </td>

                        <td className="px-3 py-2">
                          <span className="px-2 py-1 bg-zinc-800 rounded">
                            {email.intent}
                          </span>
                        </td>

                        <td className="px-3 py-2 truncate max-w-sm">
                          {email.subject}
                        </td>
                      </tr>
                    ))}
                </tbody>

              </table>
            </div>

            {/* INSPECTOR PANEL (aligned with header, inset w/ margins) */}
            <div className="w-[480px] rounded-xl border border-zinc-800 bg-zinc-900
                            flex flex-col mr-2 mb-2">

              {/* PANEL HEADER */}
              <div className="p-4 border-b border-zinc-800 flex gap-2">

                {selectedEmail?.status === "open" && (
                  <button
                    onClick={() => assignEmail(selectedEmail.id)}
                    className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500"
                  >
                    📌 Assign for review
                  </button>
                )}

                {selectedEmail?.status === "in_review" && (
                  <>
                    <button
                      onClick={() => resolveEmail(selectedEmail.id)}
                      className="px-3 py-1 rounded bg-green-600 hover:bg-green-500"
                    >
                      ✔ Resolve
                    </button>

                    <button
                      onClick={() => unassignEmail(selectedEmail.id)}
                      className="px-3 py-1 rounded bg-zinc-700 hover:bg-zinc-600"
                    >
                      ↩ Release assignment
                    </button>
                  </>
                )}

                <button
                  className="ml-auto px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700"
                  onClick={() => setSelectedEmail(null)}
                >
                  Close
                </button>
              </div>

              {/* PANEL BODY */}
              <div className="flex-1 overflow-y-auto p-4">

                {!selectedEmail && (
                  <div className="opacity-60 text-sm">
                    📨 Select an email to view details
                  </div>
                )}

                {selectedEmail && !loadingDetail && (
                  <div className="space-y-3">

                    <h2 className="text-lg font-semibold">
                      {selectedEmail.subject}
                    </h2>

                    <div className="text-sm opacity-80">
                      From: {selectedEmail.from_name ?? "(Unknown)"}{" "}
                      &lt;{selectedEmail.from_email}&gt;
                    </div>

                    {selectedEmail.assignee_name && (
                      <div className="text-sm text-purple-300">
                        Assigned to: {selectedEmail.assignee_name} —{" "}
                        {selectedEmail.assignee_email}
                      </div>
                    )}

                    <p className="font-semibold">
                      Risk Score:{" "}
                      <span className={riskColor(selectedEmail.risk_score)}>
                        {selectedEmail.risk_score.toFixed(2)}
                      </span>
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
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
