"use client";

import React, { useState } from "react";
import { Search, Loader2 } from "lucide-react";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    
    setLoading(true);
    setResults("");
    
    try {
      const res = await fetch(`http://localhost:8000/api/search?q=${encodeURIComponent(query)}`);
      
      if (res.ok) {
        const data = await res.json();
        setResults(data.results);
      } else {
        setResults("Error: Failed to fetch results.");
      }
    } catch (err) {
      console.error(err);
      setResults("Error: Could not connect to search endpoint.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-xl p-6 shadow-lg shadow-black/50">
      <div className="flex items-center space-x-3 mb-6">
        <Search className="text-emerald-400 w-6 h-6" />
        <h2 className="text-xl font-semibold">Search Memory</h2>
      </div>
      
      <form onSubmit={handleSearch} className="space-y-4">
        <div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., How is auth handled?"
            className="w-full bg-neutral-900 border border-neutral-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-white placeholder-neutral-600"
          />
        </div>
        
        <button
          type="submit"
          disabled={loading || !query}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 disabled:cursor-not-allowed text-white font-medium rounded-lg px-4 py-2.5 transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Searching...
            </>
          ) : (
            "Search"
          )}
        </button>
      </form>
      
      {results && (
        <div className="mt-4 p-4 bg-neutral-900 border border-neutral-700 rounded-lg max-h-60 overflow-y-auto">
          <p className="text-sm text-neutral-300 whitespace-pre-wrap">{results}</p>
        </div>
      )}
    </div>
  );
}
