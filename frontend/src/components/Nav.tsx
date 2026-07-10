"use client";

import React from "react";
import { motion } from "motion/react";
import { PhosphorIcon } from "@phosphor-icons/react";

export default function Nav() {
  return (
    <motion.nav 
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-6 left-1/2 -translate-x-1/2 z-50 w-[90%] max-w-4xl"
    >
      <div className="backdrop-blur-xl bg-zinc-900/40 border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] rounded-full px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-blue-600 rounded-full animate-pulse" />
          <span className="text-white font-semibold tracking-tight text-sm">Glance</span>
        </div>
        
        <div className="hidden md:flex items-center gap-8 text-zinc-400 text-xs font-medium">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#trust" className="hover:text-white transition-colors">Trust</a>
          <a href="#specs" className="hover:text-white transition-colors">Specs</a>
        </div>

        <button className="bg-white text-zinc-950 px-4 py-1.5 rounded-full text-xs font-bold hover:scale-105 active:scale-95 transition-all">
          Download
        </button>
      </div>
    </motion.nav>
  );
}
