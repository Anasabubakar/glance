"use client";

import React from "react";
import { motion } from "motion/react";

const specs = [
  { label: "Core Brain", value: "Claude 3.5 Sonnet", status: "online" },
  { label: "Ear", value: "Deepgram Streaming", status: "online" },
  { label: "Voice", value: "Edge High-Fidelity", status: "online" },
  { label: "Platform", value: "Windows / Linux", status: "stable" },
  { label: "Latency", value: "< 200ms", status: "optimal" },
  { label: "Safety", value: "Reversible Layer", status: "active" },
];

export default function BrainSpecs() {
  return (
    <section id="specs" className="py-24 px-6 md:px-12 max-w-7xl mx-auto">
      <div className="relative max-w-3xl mx-auto">
        <div className="absolute -inset-4 bg-blue-600/10 blur-3xl rounded-full opacity-50 pointer-events-none" />
        
        <div className="relative bg-zinc-900 border border-white/10 rounded-[2.5rem] p-8 md:p-12 overflow-hidden">
          <div className="flex items-center justify-between mb-12">
            <div>
              <h2 className="text-3xl font-bold text-white tracking-tighter">The Brain.</h2>
              <p className="text-zinc-500 text-sm">Technical architecture & providers</p>
            </div>
            <div className="flex gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <div className="w-2 h-2 rounded-full bg-zinc-700" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
            {specs.map((spec, i) => (
              <div key={i} className="flex items-center justify-between py-3 border-b border-white/5 group">
                <span className="text-zinc-500 text-xs font-medium group-hover:text-zinc-300 transition-colors">
                  {spec.label}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-white text-xs font-mono">{spec.value}</span>
                  <span className={`text-[8px] uppercase px-1.5 py-0.5 rounded border ${
                    spec.status === 'online' ? 'border-green-500/30 text-green-500 bg-green-500/5' : 
                    spec.status === 'stable' ? 'border-blue-500/30 text-blue-500 bg-blue-500/5' : 
                    'border-zinc-500/30 text-zinc-500 bg-zinc-500/5'
                  }`}>
                    {spec.status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-12 pt-8 border-t border-white/10 flex justify-between items-center">
            <div className="text-[10px] font-mono text-zinc-600">
              v0.1.0-alpha // build_2026_07_10
            </div>
            <div className="text-[10px] font-mono text-blue-500 cursor-pointer hover:underline">
              View Full API Docs →
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
