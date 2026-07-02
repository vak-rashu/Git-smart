"use client"
import { useEffect, useState } from 'react';

export default function MemoryExplorer() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/memory/explorer')
      .then((res) => res.json())
      .then((d) => setData(d))
      .catch((e) => console.error(e));
  }, []);

  if (!data) {
    return (
      <div className="bg-gray-900/50 rounded-xl p-6 border border-gray-800 animate-pulse mt-8">
        <div className="h-6 w-48 bg-gray-700 rounded mb-4"></div>
        <div className="grid grid-cols-3 gap-4">
          <div className="h-20 bg-gray-800 rounded"></div>
          <div className="h-20 bg-gray-800 rounded"></div>
          <div className="h-20 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/50 backdrop-blur-xl rounded-xl p-6 border border-gray-800 shadow-2xl transition-all hover:border-gray-700 mt-8">
      <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
        <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        Repository Memory Explorer
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-800/50 p-4 rounded-lg flex flex-col items-center justify-center border border-gray-700">
          <span className="text-3xl font-bold text-blue-400">{data.files_ingested}</span>
          <span className="text-sm text-gray-400 mt-1">Files Ingested</span>
        </div>
        <div className="bg-gray-800/50 p-4 rounded-lg flex flex-col items-center justify-center border border-gray-700">
          <span className="text-3xl font-bold text-purple-400">{data.active_nodes}</span>
          <span className="text-sm text-gray-400 mt-1">Graph Nodes</span>
        </div>
        <div className="bg-gray-800/50 p-4 rounded-lg flex flex-col items-center justify-center border border-gray-700">
          <span className="text-3xl font-bold text-green-400">{data.edges}</span>
          <span className="text-sm text-gray-400 mt-1">Connections</span>
        </div>
      </div>
    </div>
  );
}
