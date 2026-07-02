"use client";

import React, { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Clock } from "lucide-react";

type PR = {
  id: number;
  pr_number: number;
  title: string;
  status: string;
  reasoning: string;
  created_at: string;
};

export default function PRList() {
  const [prs, setPrs] = useState<PR[]>([]);
  const [activeTab, setActiveTab] = useState<"Accepted" | "Rejected">("Accepted");

  // Fetch PRs from backend (mocked for now to show UI if backend isn't populated)
  useEffect(() => {
    const fetchPRs = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/prs");
        if (res.ok) {
          const data = await res.json();
          setPrs(data);
        }
      } catch (e) {
        console.log("Backend not reachable, using mock data");
        setPrs([
          { id: 1, pr_number: 42, title: "Add Redis Caching Layer", status: "Accepted", reasoning: "Adheres to repo architecture.", created_at: new Date().toISOString() },
          { id: 2, pr_number: 43, title: "Use Memcached for auth", status: "Rejected", reasoning: "Conflicts with standard Redis pattern found in memory.", created_at: new Date().toISOString() }
        ]);
      }
    };
    fetchPRs();
    
    const interval = setInterval(fetchPRs, 5000);
    return () => clearInterval(interval);
  }, []);

  const filteredPRs = prs.filter(pr => pr.status === activeTab);

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-xl p-6 shadow-lg shadow-black/50 min-h-[500px]">
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
        Agentic PR Reviews
      </h2>
      
      <div className="flex space-x-1 bg-neutral-900 p-1 rounded-lg mb-6">
        <button
          onClick={() => setActiveTab("Accepted")}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${activeTab === "Accepted" ? "bg-emerald-500/20 text-emerald-400" : "text-neutral-400 hover:text-white hover:bg-neutral-800"}`}
        >
          Accepted PRs
        </button>
        <button
          onClick={() => setActiveTab("Rejected")}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${activeTab === "Rejected" ? "bg-red-500/20 text-red-400" : "text-neutral-400 hover:text-white hover:bg-neutral-800"}`}
        >
          Rejected PRs
        </button>
      </div>

      <div className="space-y-4">
        {filteredPRs.length === 0 ? (
          <div className="text-center py-12 text-neutral-500 flex flex-col items-center">
            <Clock className="w-8 h-8 mb-3 opacity-50" />
            <p>No PRs found in this category.</p>
          </div>
        ) : (
          filteredPRs.map(pr => (
            <div key={pr.id} className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 hover:border-neutral-700 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-white flex items-center gap-2">
                  #{pr.pr_number} - {pr.title}
                </h3>
                {pr.status === "Accepted" ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-400" />
                )}
              </div>
              <p className="text-sm text-neutral-400 mt-3 p-3 bg-black/20 rounded-md border border-neutral-800 font-mono leading-relaxed">
                <span className="text-blue-400">Agent Reasoning:</span> {pr.reasoning}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
