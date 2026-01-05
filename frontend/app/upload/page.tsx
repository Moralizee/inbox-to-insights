"use client";

import { useState } from "react";

type Mode = "single" | "bulk";

export default function UploadPage() {
  const [mode, setMode] = useState<Mode>("single");

  const [file, setFile] = useState<File | null>(null);
  const [files, setFiles] = useState<File[]>([]);

  const [result, setResult] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  function riskColor(score: number) {
    if (score >= 0.6) return "text-red-400";
    if (score >= 0.3) return "text-amber-300";
    return "text-green-400";
  }

  // ------------------------------------
  // SINGLE FILE UPLOAD
  // ------------------------------------
  async function handleSingleUpload() {
    if (!file) return;

    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://127.0.0.1:8000/parse-email", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setResult(data);
    setUploading(false);
  }

  // ------------------------------------
  // BULK UPLOAD
  // ------------------------------------
  async function handleBulkUpload() {
    if (!files.length) return;

    setUploading(true);

    const formData = new FormData();
    files.forEach(f => formData.append("files", f));

    const res = await fetch("http://127.0.0.1:8000/parse-email/bulk", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setResult(data);
    setUploading(false);
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-zinc-900 p-6 rounded-xl w-[520px]">

        {/* MODE SWITCH */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => {
              setMode("single");
              setResult(null);
              setFiles([]);
            }}
            className={`px-3 py-1 rounded ${
              mode === "single"
                ? "bg-blue-600"
                : "bg-zinc-700 hover:bg-zinc-600"
            }`}
          >
            Single Email
          </button>

          <button
            onClick={() => {
              setMode("bulk");
              setResult(null);
              setFile(null);
            }}
            className={`px-3 py-1 rounded ${
              mode === "bulk"
                ? "bg-blue-600"
                : "bg-zinc-700 hover:bg-zinc-600"
            }`}
          >
            Bulk Import
          </button>
        </div>

        {/* ============================ */}
        {/* SINGLE MODE */}
        {/* ============================ */}
        {mode === "single" && (
          <>
            <h1 className="text-xl font-semibold mb-2">
              Upload Email
            </h1>

            <small className="block opacity-70 mb-2">
              Select an .eml or .txt file to parse
            </small>

            <input
              id="emailFile"
              type="file"
              className="hidden"
              accept=".eml,.txt"
              onChange={e => {
                setFile(e.target.files?.[0] ?? null);
                setResult(null);
              }}
            />

            <div
              className="bg-zinc-800 px-3 py-2 rounded mb-3 text-sm cursor-pointer"
              onClick={() => document.getElementById("emailFile")?.click()}
            >
              {file
                ? <>Selected: {file.name}</>
                : <span className="opacity-60">Click to choose file</span>}
            </div>

            <button
              onClick={handleSingleUpload}
              disabled={!file || uploading}
              className={`px-4 py-2 rounded ${
                file
                  ? "bg-green-500 hover:bg-green-600"
                  : "bg-green-500/40 cursor-not-allowed"
              }`}
            >
              {uploading ? "Processing…" : "Parse Email"}
            </button>

            {result && (
              <div className="mt-4 bg-black/40 p-3 rounded space-y-2">

                <p><b>Subject:</b> {result.subject}</p>

                <p>
                  <b>From:</b> {result.from_name ?? "(Unknown)"}{" "}
                  &lt;{result.from_email}&gt;
                </p>

                <p><b>Domain:</b> {result.sender_domain}</p>
                <p><b>Provider:</b> {result.provider}</p>

                <p className={`pt-1 font-semibold ${riskColor(result.risk_score)}`}>
                  Risk Score: {result.risk_score}
                </p>
              </div>
            )}
          </>
        )}

        {/* ============================ */}
        {/* BULK MODE */}
        {/* ============================ */}
        {mode === "bulk" && (
          <>
            <h1 className="text-xl font-semibold mb-2">
              Bulk Email Import
            </h1>

            <small className="block opacity-70 mb-2">
              Select multiple .eml files (Shift+Click / Ctrl+Select)
            </small>

            <input
              id="bulkFiles"
              type="file"
              multiple
              className="hidden"
              accept=".eml,.txt"
              onChange={e => {
                setFiles(Array.from(e.target.files ?? []));
                setResult(null);
              }}
            />

            <div
              className="bg-zinc-800 px-3 py-2 rounded mb-3 text-sm cursor-pointer"
              onClick={() => document.getElementById("bulkFiles")?.click()}
            >
              {files.length
                ? `Selected ${files.length} files`
                : <span className="opacity-60">Click to choose files</span>}
            </div>

            <button
              onClick={handleBulkUpload}
              disabled={!files.length || uploading}
              className={`px-4 py-2 rounded ${
                files.length
                  ? "bg-green-500 hover:bg-green-600"
                  : "bg-green-500/40 cursor-not-allowed"
              }`}
            >
              {uploading ? "Processing…" : "Import Emails"}
            </button>

            {result && (
              <div className="mt-4 bg-black/40 p-3 rounded">
                <p>
                  Imported <b>{result.count}</b> emails successfully
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
