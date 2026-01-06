"use client";

import { useState } from "react";
import Link from "next/link";

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  function riskColor(score: number) {
    if (score >= 0.6) return "text-red-400";
    if (score >= 0.3) return "text-amber-300";
    return "text-green-400";
  }

  const resetUpload = () => {
    setFiles([]);
    setResult(null);
  };

  async function handleUpload() {
    if (!files.length) return;
    setUploading(true);

    const isBulk = files.length > 1;
    const formData = new FormData();
    const endpoint = isBulk 
      ? "http://127.0.0.1:8000/parse-email/bulk" 
      : "http://127.0.0.1:8000/parse-email";

    if (isBulk) {
      files.forEach(f => formData.append("files", f));
    } else {
      formData.append("file", files[0]);
    }

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-zinc-100 p-4">
      <div className="bg-zinc-900 border border-zinc-800 p-8 rounded-2xl w-full max-w-[520px] shadow-2xl transition-all">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-2xl font-bold mb-1">Upload Intelligence</h1>
            <p className="text-xs text-zinc-500 uppercase tracking-widest font-semibold">Manual Test Environment</p>
          </div>
          {result && (
            <button onClick={resetUpload} className="text-zinc-500 hover:text-white text-xs underline underline-offset-4">
              Clear & Reset
            </button>
          )}
        </div>

        {/* HIDDEN NATIVE INPUT */}
        <input
          id="emailFiles"
          type="file"
          multiple
          className="hidden"
          accept=".eml,.txt"
          onChange={(e) => {
            setFiles(Array.from(e.target.files ?? []));
            setResult(null);
          }}
        />

        {/* DROPZONE AREA */}
        <div
          className={`group border-2 border-dashed p-10 rounded-xl mb-6 text-center cursor-pointer transition-all ${
            result ? "border-emerald-500/30 bg-emerald-500/5" : "border-zinc-800 hover:border-zinc-600 bg-zinc-950/50"
          }`}
          onClick={() => !result && document.getElementById("emailFiles")?.click()}
        >
          <div className="text-3xl mb-2 transition-transform group-hover:scale-110">
            {result ? "✅" : "📂"}
          </div>
          {files.length > 0 ? (
            <div className="space-y-1">
              <p className={`text-sm font-medium ${result ? "text-emerald-400" : "text-blue-400"}`}>
                {files.length === 1 ? files[0].name : `${files.length} files processed`}
              </p>
            </div>
          ) : (
            <p className="text-sm text-zinc-500">Click to select .eml files</p>
          )}
        </div>

        {!result ? (
          <button
            onClick={handleUpload}
            disabled={!files.length || uploading}
            className={`w-full py-3 rounded-lg font-bold transition-all ${
              files.length && !uploading
                ? "bg-white text-black hover:bg-zinc-200"
                : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
            }`}
          >
            {uploading ? "Analyzing Patterns..." : "Start Analysis"}
          </button>
        ) : (
          <div className="space-y-3">
            <Link 
              href="/emails" 
              className="flex items-center justify-center w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold transition-all shadow-lg shadow-blue-900/20"
            >
              Go to Insights Dashboard →
            </Link>
          </div>
        )}

        {/* RESULT PREVIEW */}
        {result && (
          <div className="mt-8 animate-in fade-in zoom-in-95 duration-300">
            {files.length > 1 ? (
              <div className="bg-black/40 border border-zinc-800 p-4 rounded-xl flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 font-bold border border-emerald-500/20">
                  {result.count}
                </div>
                <p className="text-sm text-zinc-400 italic">Emails successfully ingested and parsed by AI.</p>
              </div>
            ) : (
              <div className="bg-black/40 border border-zinc-800 p-5 rounded-xl space-y-3 text-sm">
                <div className="flex justify-between items-center border-b border-zinc-800 pb-2 mb-2">
                  <span className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest">Instant Analysis</span>
                  <span className={`font-mono font-bold ${riskColor(result.risk_score)}`}>
                    RISK: {result.risk_score.toFixed(2)}
                  </span>
                </div>
                <p className="truncate text-zinc-300"><b className="text-zinc-500 font-medium">SUB:</b> {result.subject}</p>
                <div className="flex gap-4 pt-2">
                   <div className="flex-1">
                     <p className="text-[9px] text-zinc-500 uppercase font-bold">Sender Domain</p>
                     <p className="truncate text-xs">{result.sender_domain}</p>
                   </div>
                   <div className="flex-1 border-l border-zinc-800 pl-4">
                     <p className="text-[9px] text-zinc-500 uppercase font-bold">Status</p>
                     <p className="text-xs text-emerald-400 font-bold">Ingested</p>
                   </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}