"use client";

import React, { useState } from "react";
import { Database, Activity, GitCommit } from "lucide-react";

export default function MemoryStatus() {
  const [nodes, setNodes] = useState(0);
  
  // Mock function to simulate graph growth after ingest/push
  const simulateGrowth = () => {
    setNodes(prev => prev + Math.floor(Math.random() * 50) + 10);
  };

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-xl p-6 shadow-lg shadow-black/50">
      <div className="flex items-center space-x-3 mb-6">
        <Database className="text-emerald-400 w-6 h-6" />
        <h2 className="text-xl font-semibold">Memory Graph Status</h2>
      </div>
      
      <div className="space-y-4">
        <div className="flex justify-between items-center p-3 bg-neutral-900 rounded-lg">
          <span className="text-neutral-400 flex items-center gap-2"><Activity className="w-4 h-4"/> Active Nodes</span>
          <span className="font-mono text-emerald-400 text-lg">{nodes > 0 ? nodes : "---"}</span>
        </div>
        <div className="flex justify-between items-center p-3 bg-neutral-900 rounded-lg">
          <span className="text-neutral-400 flex items-center gap-2"><GitCommit className="w-4 h-4"/> Last Sync</span>
          <span className="font-mono text-sm">{nodes > 0 ? "Just now" : "Never"}</span>
        </div>
      </div>
      
      <button 
        onClick={simulateGrowth}
        className="mt-6 w-full text-sm text-neutral-400 hover:text-white transition-colors"
      >
        (Simulate Graph Growth)
      </button>
    </div>
  );
}
