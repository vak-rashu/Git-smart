"use client";

import React, { useState, useEffect } from "react";
import { Search, MessageSquare, Loader2, Sparkles, AlertCircle } from "lucide-react";

type PR = {
  id: number;
  pr_number: number;
  title: string;
  status: string;
};

type Message = {
  role: "user" | "assistant";
  text: string;
};

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [prList, setPrList] = useState<PR[]>([]);
  const [selectedPR, setSelectedPR] = useState<number | "">("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch pull requests on mount to populate context dropdown
  useEffect(() => {
    const fetchPRs = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/prs");
        if (res.ok) {
          const data = await res.json();
          setPrList(data);
        }
      } catch (err) {
        console.error("Failed to fetch PR list", err);
      }
    };
    fetchPRs();
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage: Message = { role: "user", text: query };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError("");
    const currentQuery = query;
    setQuery("");

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: currentQuery,
          pr_number: selectedPR === "" ? null : Number(selectedPR),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const botMessage: Message = {
          role: "assistant",
          text: data.answer || "No response received.",
        };
        setMessages((prev) => [...prev, botMessage]);
      } else {
        setError("Failed to get response from AI agent.");
      }
    } catch (err) {
      console.error(err);
      setError("Unable to connect to the backend companion service.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800/80 backdrop-blur-xl border border-neutral-700/80 rounded-2xl p-6 shadow-2xl shadow-black/80 flex flex-col h-[550px]">
      <div className="flex items-center justify-between mb-4 border-b border-neutral-700/50 pb-4">
        <div className="flex items-center space-x-3">
          <div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20">
            <Sparkles className="text-emerald-400 w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white leading-none">Codebase Companion</h2>
            <span className="text-xs text-neutral-400 mt-1 block">Powered by Cognee Memory Graph</span>
          </div>
        </div>
      </div>

      {/* Mode / PR Context Selector */}
      <div className="mb-4">
        <label className="block text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2">
          Chat Context Focus
        </label>
        <select
          id="context-pr-select"
          value={selectedPR}
          onChange={(e) => setSelectedPR(e.target.value === "" ? "" : Number(e.target.value))}
          className="w-full bg-neutral-900/60 border border-neutral-700/80 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30 transition-all cursor-pointer"
        >
          <option value="">Whole Codebase & Architecture</option>
          {prList.map((pr) => (
            <option key={pr.id} value={pr.pr_number}>
              PR #{pr.pr_number} - {pr.title}
            </option>
          ))}
        </select>
      </div>

      {/* Message Screen */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4 scrollbar-thin scrollbar-thumb-neutral-700 scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-neutral-500 p-4">
            <MessageSquare className="w-10 h-10 mb-3 opacity-40 text-emerald-400/80" />
            <p className="text-sm font-medium text-neutral-400">Ask questions about your files or pull request changes</p>
            <p className="text-xs text-neutral-600 mt-1 max-w-[240px]">
              "Will this pattern work in our database?" or "Compare the before & after logic of this fix."
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${
                msg.role === "user" ? "items-end" : "items-start"
              }`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-emerald-600/90 text-white rounded-br-none shadow-md shadow-emerald-950/20"
                    : "bg-neutral-900 border border-neutral-800 text-neutral-200 rounded-bl-none shadow-sm"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.text}</p>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center gap-2 text-neutral-500 text-sm ml-2 bg-neutral-900/40 py-1.5 px-3 rounded-full border border-neutral-850 w-fit">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
            <span>AI thinking...</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 bg-red-950/30 border border-red-900/50 rounded-xl p-3 text-red-400 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="mt-auto">
        <div className="relative flex items-center">
          <input
            id="chat-query-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              selectedPR === ""
                ? "Ask about architecture, caches, auth..."
                : "Ask about this PR changes & patterns..."
            }
            className="w-full bg-neutral-900/90 border border-neutral-700/80 rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 transition-all"
          />
          <button
            id="chat-submit-btn"
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white p-2 rounded-lg transition-colors cursor-pointer"
          >
            <Search className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
