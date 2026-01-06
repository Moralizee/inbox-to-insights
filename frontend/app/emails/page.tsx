"use client";

import { useEffect, useState, useRef } from "react";

const currentUser = { name: "N Analyst", email: "analyst@corp.local" };

// --- INTERFACES ---
interface Email {
  id: number;
  subject: string;
  from_name: string | null;
  from_email: string | null;
  category: string;
  intent: string;
  risk_score: number;
  status: "open" | "assigned" | "in_review" | "resolved";
  assignee_name?: string;
  action_items?: string[]; 
  deadlines?: string[];    
  ai_tasks?: string;       // New field from backend
}

interface EmailDetail extends Email {
  body: string;
  summary: string;         // New field from backend
  links: { url: string; domain: string }[];
  risk_flags: string[];
  action_request?: boolean;
  urgency?: string;
}

export default function EmailsDashboard() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<EmailDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [expandedBody, setExpandedBody] = useState(false);
  const tableContainerRef = useRef<HTMLDivElement>(null);

  const [filters, setFilters] = useState({ q: "", category: "", suspicious_only: false });

  // =====================================================
  // KEYBOARD NAVIGATION LOGIC
  // =====================================================
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (emails.length === 0 || e.target instanceof HTMLInputElement) return;
      
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
      }

      const currentIndex = emails.findIndex((mail) => mail.id === selectedId);

      if (e.key === "ArrowDown") {
        const nextIndex = currentIndex + 1;
        if (nextIndex < emails.length) {
          openEmail(emails[nextIndex].id);
        }
      } else if (e.key === "ArrowUp") {
        const prevIndex = currentIndex - 1;
        if (prevIndex >= 0) {
          openEmail(emails[prevIndex].id);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedId, emails]);


  // =====================================================
  // CORE LOGIC: DATA & SCROLLING
  // =====================================================
  async function loadEmails() {
    setLoading(true);
    const params = new URLSearchParams(filters as any);
    const res = await fetch(`http://127.0.0.1:8000/emails?${params.toString()}`);
    setEmails(await res.json());
    setLoading(false);
  }

  useEffect(() => { loadEmails(); }, [filters]);

  async function openEmail(id: number) {
    setSelectedId(id);
    setExpandedBody(false); 
    
    const container = tableContainerRef.current;
    const row = document.getElementById(`row-${id}`);
    if (container && row) {
      const headerHeight = 48;
      if (row.offsetTop < container.scrollTop + headerHeight) {
        container.scrollTo({ top: row.offsetTop - headerHeight });
      } else if (row.offsetTop + row.offsetHeight > container.scrollTop + container.clientHeight) {
        container.scrollTo({ top: row.offsetTop + row.offsetHeight - container.clientHeight });
      }
    }

    if (selectedEmail?.id === id) return;
    setLoadingDetail(true);
    const res = await fetch(`http://127.0.0.1:8000/emails/${id}`);
    const data = await res.json();
    setSelectedEmail(data);
    setLoadingDetail(false);
  }

  const updateLocal = (id: number, fields: Partial<EmailDetail>) => {
    setEmails(prev => prev.map(e => e.id === id ? { ...e, ...fields } : e));
    setSelectedEmail(prev => (prev?.id === id ? { ...prev, ...fields } : prev));
  };

  async function handleStatus(id: number, action: 'assign' | 'unassign' | 'resolve') {
    const method = action === 'assign' ? 'POST' : 'PUT';
    await fetch(`http://127.0.0.1:8000/emails/${id}/${action}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: action === 'assign' ? JSON.stringify({ assignee_name: currentUser.name, assignee_email: currentUser.email }) : undefined
    });
    
    if (action === 'assign') updateLocal(id, { status: 'assigned', assignee_name: currentUser.name });
    if (action === 'unassign') updateLocal(id, { status: 'open', assignee_name: "" });
    if (action === 'resolve') updateLocal(id, { status: 'resolved' });
  }

  const getRiskColor = (s: number) => s >= 0.6 ? "text-red-400" : s >= 0.3 ? "text-amber-400" : "text-emerald-400";

  const getDeadlineStyle = (dateStr: string) => {
    const days = Math.ceil((new Date(dateStr).getTime() - new Date().getTime()) / (1000 * 3600 * 24));
    if (days < 0) return "text-red-400 font-bold";
    if (days <= 2) return "text-amber-400";
    return "text-zinc-500";
  };

  return (
    <div className="h-screen bg-black text-zinc-100 flex flex-col font-sans overflow-hidden">
      
      <header className="px-8 py-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/50 backdrop-blur-md">
        <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-zinc-500 bg-clip-text text-transparent">
          INBOX INSIGHTS <span className="text-xs font-mono text-zinc-600 ml-2">v1.1 AI-ENABLED</span>
        </h1>
        <div className="flex gap-3">
          <input 
            placeholder="Search action items..." 
            className="bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg text-sm w-64 focus:ring-1 ring-zinc-700 outline-none"
            onChange={(e) => setFilters({...filters, q: e.target.value})}
          />
          <label className="flex items-center gap-2 text-xs text-zinc-400 bg-zinc-900 px-3 rounded-lg border border-zinc-800 cursor-pointer">
            <input type="checkbox" onChange={(e) => setFilters({...filters, suspicious_only: e.target.checked})} />
            High Risk Only
          </label>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden p-6 gap-6">
        
        <section className="flex-1 bg-zinc-900/20 border border-zinc-800 rounded-2xl overflow-hidden flex flex-col">
          <div ref={tableContainerRef} className="overflow-y-auto relative h-full scrollbar-hide">
            <table className="w-full text-sm text-left border-separate border-spacing-0">
              <thead className="sticky top-0 z-30 bg-zinc-950 shadow-xl">
                <tr>
                  <th className="p-4 font-medium text-zinc-500 border-b border-zinc-800">Status</th>
                  <th className="p-4 font-medium text-zinc-500 border-b border-zinc-800">Risk</th>
                  <th className="p-4 font-medium text-zinc-500 border-b border-zinc-800">Intelligence & Deadlines</th>
                  <th className="p-4 font-medium text-zinc-500 border-b border-zinc-800">Subject</th>
                </tr>
              </thead>
              <tbody>
                {emails.map(e => (
                  <tr 
                    key={e.id} id={`row-${e.id}`}
                    onClick={() => openEmail(e.id)}
                    className={`group cursor-pointer transition-colors border-b border-zinc-800/50 hover:bg-zinc-800/30 ${selectedId === e.id ? 'bg-zinc-800/60' : ''}`}
                  >
                    <td className="p-4">
                      {e.status === 'resolved' ? 
                        <span className="text-[10px] uppercase tracking-widest px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">Resolved</span> :
                        <span className="flex items-center gap-2 text-zinc-400 italic text-xs">
                           <div className={`w-1.5 h-1.5 rounded-full ${e.status === 'assigned' ? 'bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.5)]' : 'bg-zinc-600'}`} />
                           {e.status === 'assigned' ? e.assignee_name : 'Unassigned'}
                        </span>
                      }
                    </td>
                    <td className={`p-4 font-mono font-medium ${getRiskColor(e.risk_score)}`}>{e.risk_score.toFixed(2)}</td>
                    <td className="p-4">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400 font-bold uppercase border border-zinc-700">Action</span>
                          {/* Use ai_tasks for table preview if available */}
                          <span className="text-xs text-zinc-300 truncate max-w-[150px]">{e.ai_tasks?.split(';')[0] || e.intent.replace(/_/g, ' ')}</span>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 truncate max-w-xs font-medium text-zinc-200">{e.subject || "(No Subject)"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="w-[480px] bg-zinc-900 border border-zinc-800 rounded-2xl flex flex-col shadow-2xl overflow-hidden">
          {selectedEmail ? (
            <>
              <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-zinc-950/30 rounded-t-2xl">
                <div className="flex gap-2">
                  {selectedEmail.status === 'open' ? (
                    <button onClick={() => handleStatus(selectedEmail.id, 'assign')} className="px-4 py-1.5 bg-white text-black rounded-lg text-xs font-bold hover:bg-zinc-200 transition">Assign to Me</button>
                  ) : selectedEmail.status === 'assigned' ? (
                    <>
                      <button onClick={() => handleStatus(selectedEmail.id, 'resolve')} className="px-4 py-1.5 bg-emerald-600 rounded-lg text-xs font-bold hover:bg-emerald-500 transition">Resolve</button>
                      <button onClick={() => handleStatus(selectedEmail.id, 'unassign')} className="px-4 py-1.5 bg-zinc-800 rounded-lg text-xs font-bold hover:bg-zinc-700 transition">Release</button>
                    </>
                  ) : <span className="text-emerald-400 text-xs font-bold">Case Resolved</span>}
                </div>
                <button onClick={() => setSelectedId(null)} className="text-zinc-500 hover:text-white transition">✕</button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-8">
                <div>
                  <h2 className="text-lg font-bold leading-tight break-words">{selectedEmail.subject || "(No Subject)"}</h2>
                  <div className="mt-2 flex items-center gap-2 text-xs text-zinc-500 font-mono">
                    <span className="text-zinc-300 truncate max-w-[200px]">{selectedEmail.from_email}</span>
                    <span>•</span>
                    <span className="uppercase">{selectedEmail.category}</span>
                  </div>
                </div>

                {/* --- RENDERING SUMMARY SECTION --- */}
                <div className="space-y-3">
                  <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest">AI Executive Summary</label>
                  <div className="p-4 bg-blue-500/5 rounded-xl border border-blue-500/10 italic">
                    <p className="text-sm text-zinc-300 leading-relaxed">
                      "{selectedEmail.summary || "No summary available."}"
                    </p>
                  </div>
                </div>

                {/* --- RENDERING CHECKLIST FROM ai_tasks --- */}
                <div className="space-y-3">
                  <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest">Priority Actions</label>
                  <div className="space-y-2">
                    {selectedEmail.ai_tasks ? selectedEmail.ai_tasks.split('; ').map((item, i) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-zinc-800/30 rounded-lg border border-zinc-800 group transition-colors">
                        <input type="checkbox" className="mt-1 w-4 h-4 rounded border-zinc-700 bg-black text-blue-500 focus:ring-0" />
                        <span className="text-sm text-zinc-300 leading-snug">{item}</span>
                      </div>
                    )) : <p className="text-xs text-zinc-600 italic">No specific actions detected.</p>}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-y border-zinc-800 py-6">
                  <div>
                    <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest">Risk Score</label>
                    <p className={`text-2xl font-mono font-black ${getRiskColor(selectedEmail.risk_score)}`}>{selectedEmail.risk_score.toFixed(2)}</p>
                  </div>
                  <div>
                    <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest">Intent</label>
                    <p className="text-zinc-100 font-medium capitalize">{selectedEmail.intent.replace(/_/g, ' ')}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                    <label className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest">Original Content</label>
                    <button 
                      onClick={() => setExpandedBody(!expandedBody)}
                      className="text-[10px] text-blue-400 hover:text-blue-300 font-bold uppercase tracking-tight transition-colors"
                    >
                      {expandedBody ? "Collapse" : "Show Full Text"}
                    </button>
                  </div>
                  <div className={`bg-black/40 border border-zinc-800 p-4 rounded-xl text-sm leading-relaxed text-zinc-400 font-serif italic transition-all overflow-hidden break-words ${!expandedBody ? 'line-clamp-4' : ''}`}>
                    {selectedEmail.body || "No body content available."}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-700">
              <div className="w-12 h-12 border-2 border-dashed border-zinc-800 rounded-full mb-4 flex items-center justify-center text-lg">?</div>
              <p className="text-xs uppercase tracking-widest font-bold">Waiting for selection</p>
              <p className="text-[10px] mt-2 text-zinc-600">Use arrow keys to navigate</p>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}