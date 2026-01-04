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

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-zinc-900 p-6 rounded-xl w-[420px]">

        <h1 className="text-xl font-semibold mb-4">
          Upload Email
        </h1>

        {/* Text only — NOT clickable */}
        <p className="text-sm font-medium">Choose file :</p>

        <small className="block opacity-70 mb-2">
          Select an .eml or .txt file to parse
        </small>

        {/* Hidden input — NOT linked to a label */}
        <input
          type="file"
          id="emailFile"
          className="hidden"
          accept=".eml,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />

        {/* Browse button — own line */}
        <button
          type="button"
          onClick={() => document.getElementById("emailFile")?.click()}
          className="mt-2 px-3 py-2 rounded bg-zinc-700 hover:bg-zinc-600 w-fit block"
        >
          {file ? `Selected: ${file.name}` : "Browse"}
        </button>

        {/* Parse Email — below Browse */}
        <button
          onClick={handleUpload}
          disabled={!file}
          className={`mt-4 px-4 py-2 rounded w-fit block
            ${
              file
                ? "bg-green-500 hover:bg-green-600"
                : "bg-green-500/40 cursor-not-allowed"
            }`}
        >
          Parse Email
        </button>

        {result && (
          <div className="mt-4 bg-black/40 p-3 rounded">
            <p><b>Subject:</b> {result.subject}</p>
            <p><b>From:</b> {result.from}</p>
            <p><b>Preview:</b> {result.preview}</p>
          </div>
        )}
      </div>
    </div>
  );
}
