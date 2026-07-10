"use client";

import React from "react";
import { motion } from "motion/react";
import { Eye, CursorClick, Gear, Zap } from "@phosphor-icons/react";

const tiles = [
  {
    title: "Visual Intelligence",
    desc: "Glance sees your entire desktop in real-time, understanding context across multiple windows.",
    icon: <Eye size={24} />,
    size: "md:col-span-2",
    content: (
      <div className="relative h-full w-full bg-zinc-900 rounded-2xl border border-white/5 overflow-hidden p-6">
        <div className="absolute inset-0 pointer-events-none">
          <motion.div 
            className="absolute w-full h-1 bg-blue-500/30 blur-sm"
            animate={{ top: ["0%", "100%", "0%"] }}
            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          />
        </div>
        <div className="grid grid-cols-2 gap-4 h-full">
          <div className="bg-zinc-800/50 rounded-lg border border-white/5 p-4 space-y-2">
            <div className="h-2 w-1/2 bg-zinc-700 rounded" />
            <div className="h-2 w-3/4 bg-zinc-700 rounded" />
          </div>
          <div className="bg-zinc-800/50 rounded-lg border border-white/5 p-4 space-y-2">
            <div className="h-2 w-1/3 bg-zinc-700 rounded" />
            <div className="h-2 w-2/3 bg-zinc-700 rounded" />
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Pixel Precise",
    desc: "Not just coordinates. The Buddy snaps to real UI elements with surgical accuracy.",
    icon: <CursorClick size={24} />,
    size: "md:col-span-1",
    content: (
      <div className="relative h-full w-full bg-zinc-900 rounded-2xl border border-white/5 overflow-hidden p-6 flex items-center justify-center">
        <div className="w-20 h-20 bg-zinc-800 rounded-lg border border-white/10 relative">
          <motion.div 
            className="absolute w-4 h-4 bg-blue-500 rounded-full blur-[2px]"
            animate={{ 
              x: [0, 40, 20, 0], 
              y: [0, 20, 40, 0] 
            }}
            transition={{ duration: 3, repeat: Infinity, type: "spring" }}
          />
        </div>
      </div>
    )
  },
  {
    title: "Autonomous Action",
    desc: "From opening apps to managing files, Glance executes complex workflows while you talk.",
    icon: <Zap size={24} />,
    size: "md:col-span-1",
    content: (
      <div className="relative h-full w-full bg-zinc-900 rounded-2xl border border-white/5 overflow-hidden p-6 font-mono text-[10px] text-zinc-500 space-y-2">
        <div className="flex gap-2">
          <span className="text-blue-500">[EXEC]</span>
          <span>Open Notion</span>
        </div>
        <div className="flex gap-2">
          <span className="text-blue-500">[EXEC]</span>
          <span>Create Page 'Daily'</span>
        </div>
        <div className="flex gap-2">
          <span className="text-blue-500">[EXEC]</span>
          <span>Insert Template...</span>
        </div>
        <motion.div 
          className="h-1 w-full bg-zinc-800 rounded overflow-hidden"
        >
          <motion.div 
            className="h-full bg-blue-500"
            animate={{ x: ["-100%", "100%"] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          />
        </motion.div>
      </div>
    )
  },
  {
    title: "Infinite Memory",
    desc: "Learns your routines and remembers preferences across sessions.",
    icon: <Gear size={24} />,
    size: "md:col-span-2",
    content: (
      <div className="relative h-full w-full bg-zinc-900 rounded-2xl border border-white/5 overflow-hidden p-6">
        <div className="flex gap-4 overflow-hidden">
          {[1, 2, 3].map(i => (
            <motion.div 
              key={i}
              className="min-w-[140px] h-24 bg-zinc-800/50 rounded-xl border border-white/5 p-3 space-y-2"
              animate={{ x: [0, -10, 0] }}
              transition={{ duration: 4, delay: i * 0.5, repeat: Infinity }}
            >
              <div className="h-2 w-1/2 bg-zinc-700 rounded" />
              <div className="h-2 w-3/4 bg-zinc-700 rounded" />
              <div className="h-2 w-1/4 bg-zinc-700 rounded" />
            </motion.div>
          ))}
        </div>
      </div>
    )
  }
];

export default function BentoGrid() {
  return (
    <section id="features" className="py-24 px-6 md:px-12 max-w-7xl mx-auto">
      <div className="text-center mb-16 space-y-4">
        <h2 className="text-4xl md:text-6xl font-bold text-white tracking-tighter">The Core Loop.</h2>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto">A seamless cycle of perception, pointing, and execution.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tiles.map((tile, idx) => (
          <motion.div 
            key={idx}
            className={`${tile.size} group`}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: idx * 0.1 }}
          >
            <div className="h-full bg-zinc-900/50 border border-white/10 rounded-[2.5rem] p-8 flex flex-col gap-6 hover:border-blue-500/50 transition-colors group-hover:bg-zinc-900/80">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-600/10 text-blue-500 rounded-2xl flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-all">
                  {tile.icon}
                </div>
                <h3 className="text-xl font-bold text-white">{tile.title}</h3>
              </div>
              <p className="text-zinc-400 text-sm leading-relaxed">{tile.desc}</p>
              <div className="flex-1 min-h-[200px]">
                {tile.content}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
