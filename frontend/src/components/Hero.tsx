"use client";

import React from "react";
import { motion } from "motion/react";

export default function Hero() {
  return (
    <section className="relative min-h-[100dvh] flex items-center px-6 md:px-12 max-w-7xl mx-auto pt-20">
      <div className="grid grid-cols-1 md:grid-cols-12 gap-12 w-full items-center">
        {/* Left: Typography */}
        <div className="md:col-span-7 space-y-8">
          <motion.div
            initial={{ x: -50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ type: "spring", stiffness: 100, damping: 20 }}
          >
            <h1 className="text-5xl md:text-8xl font-bold tracking-tighter leading-[0.9] text-white">
              Talk to your <br />
              <span className="text-zinc-500">computer.</span> <br />
              She actually <br />
              <span className="text-blue-500">does it.</span>
            </h1>
          </motion.div>

          <motion.p 
            initial={{ x: -30, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 100, damping: 20 }}
            className="text-zinc-400 text-lg md:text-xl max-w-[50ch] leading-relaxed"
          >
            A voice-first AI companion that sees your screen, points at what you need, 
            and executes multi-step tasks while you keep working.
          </motion.p>

          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4, type: "spring", stiffness: 100, damping: 20 }}
            className="flex items-center gap-4"
          >
            <button className="bg-blue-600 text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-blue-500 transition-all active:scale-95 shadow-lg shadow-blue-600/20">
              Get Glance
            </button>
            <button className="text-zinc-500 hover:text-white transition-colors font-medium text-sm underline underline-offset-4">
              Watch Demo
            </button>
          </motion.div>
        </div>

        {/* Right: The Buddy Visual */}
        <div className="md:col-span-5 relative h-[400px] md:h-[600px] flex items-center justify-center">
          <motion.div 
            className="relative w-full h-full max-w-md"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.6, type: "spring", stiffness: 50, damping: 20 }}
          >
            {/* Simulated Window */}
            <div className="absolute inset-0 bg-zinc-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden p-4">
              <div className="flex gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-500/50" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                <div className="w-3 h-3 rounded-full bg-green-500/50" />
              </div>
              <div className="space-y-3">
                <div className="h-4 w-3/4 bg-zinc-800 rounded animate-pulse" />
                <div className="h-4 w-1/2 bg-zinc-800 rounded animate-pulse" />
                <div className="h-4 w-5/6 bg-zinc-800 rounded animate-pulse" />
                <div className="h-20 w-full bg-zinc-800/50 rounded-xl border border-white/5" />
                <div className="h-4 w-2/3 bg-zinc-800 rounded animate-pulse" />
              </div>
            </div>

            {/* The Buddy - Floating Sphere */}
            <motion.div 
              className="absolute w-12 h-12 bg-blue-500 rounded-full blur-sm opacity-80"
              animate={{ 
                x: [0, 80, -40, 20, 0], 
                y: [0, -60, 40, -20, 0],
                scale: [1, 1.2, 0.8, 1.1, 1]
              }}
              transition={{ 
                duration: 8, 
                repeat: Infinity, 
                ease: "linear" 
              }}
            />
            <motion.div 
              className="absolute w-10 h-10 bg-blue-400 rounded-full shadow-[0_0_20px_rgba(59,130,246,0.5)]"
              animate={{ 
                x: [0, 80, -40, 20, 0], 
                y: [0, -60, 40, -20, 0],
                scale: [1, 1.2, 0.8, 1.1, 1]
              }}
              transition={{ 
                duration: 8, 
                repeat: Infinity, 
                ease: "linear" 
              }}
            />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
