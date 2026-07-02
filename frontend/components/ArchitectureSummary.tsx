"use client"
import { useEffect, useState } from 'react';

export default function ArchitectureSummary() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/memory/explorer')
      .then((res) => res.json())
      .then((d) => setData(d))
      .catch((e) => console.error(e));
  }, []);

  if (!data) return null;

  return (
    <div className="bg-gray-900/50 backdrop-blur-xl rounded-xl p-6 border border-gray-800 shadow-2xl transition-all hover:border-gray-700 mt-8">
      <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
        <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
        Architecture Summary
      </h2>
      <p className="text-gray-300 leading-relaxed border-l-4 border-blue-500 pl-4 bg-gray-800/30 p-4 rounded-r-lg">
        {data.architecture_summary}
      </p>
    </div>
  );
}
