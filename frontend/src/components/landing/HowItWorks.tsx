"use client";

import { motion } from "motion/react";

const steps = [
  {
    number: "01",
    title: "Summon",
    detail: "Hold Ctrl + Alt + M",
    description:
      "Press the hotkey anywhere on your desktop. Glance appears instantly as a floating cursor buddy, ready to help.",
  },
  {
    number: "02",
    title: "Speak",
    detail: "Ask anything naturally",
    description:
      "Talk to Glance like a person. Ask it to find a button, fill out a form, or explain what's on your screen.",
  },
  {
    number: "03",
    title: "Watch",
    detail: "Glance answers, points, acts",
    description:
      "It reads your screen in real-time, points at the right elements, and performs actions — clicks, types, scrolls — for you.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="relative px-6 py-24 md:py-32">
      <div className="mx-auto max-w-[1200px]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="font-grotesk text-[11px] font-medium uppercase tracking-[0.2em] text-indigo mb-4 block">
            How it Works
          </span>
          <h2 className="font-serif italic text-3xl sm:text-4xl md:text-[44px] leading-tight">
            Three seconds to magic
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.5, delay: i * 0.15 }}
              className="relative rounded-2xl border border-border-subtle bg-bg-card/30 p-8 overflow-hidden group hover:border-border-medium transition-colors"
            >
              <div className="absolute top-4 right-6 text-7xl font-bold text-white/[0.03] leading-none select-none">
                {step.number}
              </div>

              <div className="relative z-10">
                <div className="text-indigo font-mono text-sm font-medium mb-4">
                  {step.number}
                </div>
                <h3 className="text-xl font-semibold mb-1">{step.title}</h3>
                <p className="text-indigo text-sm font-medium mb-4">
                  {step.detail}
                </p>
                <p className="text-text-muted text-sm leading-relaxed">
                  {step.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
