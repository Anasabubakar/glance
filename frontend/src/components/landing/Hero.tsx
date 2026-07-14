"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "motion/react";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-24 pb-16 overflow-hidden">
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[600px] h-[600px] rounded-full bg-indigo/10 blur-[120px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 flex flex-col items-center text-center"
      >
        <div className="relative mb-8">
          <div className="absolute inset-0 w-[200px] h-[200px] rounded-full bg-indigo/20 blur-[60px] -translate-x-1/2 -translate-y-1/2 left-1/2 top-1/2" />
          <Image
            src="/glance.png"
            alt="Glance 3D Logo"
            width={200}
            height={202}
            priority
            className="relative z-10 drop-shadow-2xl"
          />
        </div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="font-serif italic text-5xl sm:text-6xl md:text-7xl leading-[1.1] mb-6 max-w-[900px]"
        >
          Your Intelligent Cursor
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.35 }}
          className="text-text-muted text-base sm:text-lg max-w-[520px] mb-10 leading-relaxed"
        >
          A voice-first AI companion that sees your screen, understands what
          you&apos;re doing, and helps you do it faster.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="flex flex-col sm:flex-row items-center gap-4 mb-8"
        >
          <Link
            href="#download"
            className="px-8 py-3.5 rounded-xl bg-gradient-brand text-white font-medium text-base glow-brand hover:opacity-90 transition-all"
          >
            Download Free
          </Link>
          <Link
            href="https://github.com/Anasabubakar/glance"
            target="_blank"
            rel="noopener noreferrer"
            className="px-8 py-3.5 rounded-xl border border-border-medium text-text-muted font-medium text-base hover:text-text-primary hover:border-text-muted transition-all"
          >
            View on GitHub
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.65 }}
          className="flex items-center gap-2 px-4 py-2 rounded-full bg-bg-surface border border-border-subtle"
        >
          <kbd className="px-2 py-0.5 rounded bg-bg-card text-[11px] font-mono text-text-muted border border-border-subtle">
            Ctrl
          </kbd>
          <span className="text-text-dim text-xs">+</span>
          <kbd className="px-2 py-0.5 rounded bg-bg-card text-[11px] font-mono text-text-muted border border-border-subtle">
            Alt
          </kbd>
          <span className="text-text-dim text-xs">+</span>
          <kbd className="px-2 py-0.5 rounded bg-bg-card text-[11px] font-mono text-text-muted border border-border-subtle">
            M
          </kbd>
          <span className="text-text-muted text-xs ml-1">to summon</span>
        </motion.div>
      </motion.div>
    </section>
  );
}
