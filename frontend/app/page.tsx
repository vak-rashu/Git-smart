import React from "react";
import PRList from "../components/PRList";
import IngestForm from "../components/IngestForm";
import MemoryExplorer from "../components/MemoryExplorer";
import SearchBar from "../components/SearchBar";

export default function Home() {
  return (
    <main className="min-h-screen bg-neutral-900 text-white p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="border-b border-neutral-800 pb-6">
          <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
            GitHub Native Companion
          </h1>
          <p className="text-neutral-400 mt-2">
            Powered by Cognee Memory & OpenClaw Orchestration
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="col-span-1 space-y-8">
            <IngestForm />
            <SearchBar />
          </div>
          
          <div className="col-span-1 md:col-span-2 flex flex-col gap-8">
            <MemoryExplorer />
            <PRList />
          </div>
        </div>
      </div>
    </main>
  );
}
