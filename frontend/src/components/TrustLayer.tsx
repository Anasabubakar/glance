"use client";

import React from "react";
import { motion } from "motion/react";
import { ArrowLeft, ArrowRight, Undo } from "@phosphor-icons/react";

export default function TrustLayer() {
  return (
    <section id="trust" className="py-24 px-6 md:px-12 max-w-7xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <div className="space-y-8">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-600/10 border border-blue-500/20 text-blue-500 text-xs font-bold tracking-wide uppercase"
          >
            <Undo size={14} />
            <span>The Trust Layer</span>
          </motion.div>
          
          <h2 className="text-4xl md:text-6xl font-bold text-white tracking-tighter leading-none">
            Autonomous by default. <br />
            <span className="text-zinc-500">Reversible always.</span>
          </h2>
          
          <p className="text-zinc-400 text-lg max-w-[55ch] leading-relaxed">
            Glance doesn't just act; it journals. Every file move, rename, or creation 
            is tracked in a reversible batch. One word, and the entire session 
            snaps back to exactly how it was.
          </p>
        </div>

        <div className="relative aspect-square md:aspect-video bg-zinc-900 rounded-[2.5rem] border border-white/10 p-8 overflow-hidden group">
          {/* Live Action Side */}
          <div className="absolute inset-0 flex">
            <div className="w-1/2 h-full border-r border-white/5 p-4 space-y-4">
              <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-4">Active Session</div>
              {[1, 2, 3, 4, 5].map(i => (
                <motion.div 
                  key={i}
                  initial={{ x: -20, opacity: 0 }}
                  whileInView={{ x: 0, opacity: 1 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-center gap-3 text-xs text-zinc-400"
                >
                  <ArrowRight size={12} className="text-blue-500" />
                  <span className="truncate">file_{i}.pdf → /Archive/2024/</span>
                </motion.div>
              ))}
            </div>

            {/* Undo Side */}
            <div className="w-1/2 h-full p-4 flex flex-col items-center justify-center gap-6">
              <motion.button 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="w-20 h-20 rounded-full bg-white text-zinc-950 flex items-center justify-center shadow-2xl group-hover:shadow-blue-500/20 transition-all"
              >
                <Undo size={32} weight="bold" />
              </motion.button>
              <div className="text-center">
                <div className="text-xs font-bold text-white uppercase tracking-widest">Undo Batch</div>
                <div className="text-[10px] text-zinc-500">Revert 5 operations</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
