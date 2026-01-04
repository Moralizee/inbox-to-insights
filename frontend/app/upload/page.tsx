"use client";

import { useState } from "react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);

  async function handleUpload() {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://127.0.0.1:8000/parse-email", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setResult(data);
  }

  function chooseFile() {
    document.getElementById("emailFile")?.click();
  }

  function riskColor(score: number) {
    if (score >= 0.6) return "text-red-400";
    if (score >= 0.3) return "text-amber-300";
    return "text-green-400";
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-zinc-900 p-6 rounded-xl w-[480px]">

        <h1 className="text-xl font-semibold mb-4">
          Upload Email
        </h1>

        <p className="text-sm font-medium">Choose file :</p>
        <small className="block opacity-70 mb-2">
          Select an .eml or .txt file to parse
        </small>

        {/* Hidden file input */}
        <input
          id="emailFile"
          type="file"
          className="hidden"
          accept=".eml,.txt"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
          }}
        />

        {/* Selected file display */}
        <div className="bg-zinc-800 px-3 py-2 rounded mb-3 text-sm">
          {file ? <>Selected: {file.name}</> : <span className="opacity-60">No file selected</span>}
        </div>

        {/* File actions */}
        <button
          type="button"
          onClick={chooseFile}
          className="px-3 py-2 rounded bg-zinc-700 hover:bg-zinc-600 mr-2"
        >
          {file ? "Choose another file" : "Browse"}
        </button>

        <button
          onClick={handleUpload}
          disabled={!file}
          className={`px-4 py-2 rounded ${
            file
              ? "bg-green-500 hover:bg-green-600"
              : "bg-green-500/40 cursor-not-allowed"
          }`}
        >
          Parse Email
        </button>

        {/* ---- Parsed Output ---- */}
        {result && (
          <div className="mt-4 bg-black/40 p-3 rounded space-y-2">

            {/* Subject */}
            <p><b>Subject:</b> {result.subject}</p>

            {/* Sender */}
            <p>
              <b>From:</b> {result.from_name ?? "(Unknown)"}{" "}
              &lt;{result.from_email}&gt;
            </p>

            <p><b>Domain:</b> {result.sender_domain}</p>
            <p><b>Provider:</b> {result.provider}</p>

            {result.is_noreply && (
              <p className="text-amber-300">⚠️ This is a no-reply system email</p>
            )}

            {/* --- Category / Intent --- */}
            <div className="pt-2 flex gap-2 text-sm">
              <span className="px-2 py-1 rounded bg-zinc-800">
                🏷 Category: <b>{result.category}</b>
              </span>

              <span className="px-2 py-1 rounded bg-zinc-800">
                🎯 Intent: <b>{result.intent}</b>
              </span>
            </div>

            {/* --- Risk Score --- */}
            <p className={`pt-1 font-semibold ${riskColor(result.risk_score)}`}>
              Risk Score: {result.risk_score}
            </p>

            {/* Risk Flags */}
            {result.risk_flags?.length > 0 && (
              <ul className="list-disc ml-4 text-amber-300 text-sm">
                {result.risk_flags.map((f: string, i: number) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            )}

            {/* --- Extracted Links --- */}
            {result.links?.length > 0 && (
              <div className="pt-2 text-sm">
                <b>Links found:</b>
                <ul className="mt-1 space-y-1">
                  {result.links.map((l: any, i: number) => (
                    <li key={i} className="truncate">
                      🔗 <a
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

            {/* Preview */}
            <p className="pt-2">
              <b>Preview:</b> {result.preview}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
