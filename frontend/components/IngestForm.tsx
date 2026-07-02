"use client";

import React, { useState } from "react";
import { Github, Loader2 } from "lucide-react";

export default function IngestForm() {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;
    
    setLoading(true);
    setStatus("idle");
    
    try {
      const res = await fetch("http://localhost:8000/api/repo/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      
      if (res.ok) {
        setStatus("success");
        setRepoUrl("");
      } else {
        setStatus("error");
      }
    } catch (err) {
      console.error(err);
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-xl p-6 shadow-lg shadow-black/50">
      <div className="flex items-center space-x-3 mb-6">
        <Github className="text-blue-400 w-6 h-6" />
        <h2 className="text-xl font-semibold">Connect Repository</h2>
      </div>
      
      <form onSubmit={handleIngest} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-neutral-400 mb-2">
            GitHub Repository URL
          </label>
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="e.g., https://github.com/org/repo"
            className="w-full bg-neutral-900 border border-neutral-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all text-white placeholder-neutral-600"
          />
        </div>
        
        <button
          type="submit"
          disabled={loading || !repoUrl}
          className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-700 disabled:cursor-not-allowed text-white font-medium rounded-lg px-4 py-2.5 transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Ingesting...
            </>
          ) : (
            "Ingest to Memory"
          )}
        </button>
        
        {status === "success" && (
          <p className="text-emerald-400 text-sm text-center">Repository ingested successfully!</p>
        )}
        {status === "error" && (
          <p className="text-red-400 text-sm text-center">Failed to ingest repository.</p>
        )}
      </form>
    </div>
  );
}
