"use client";

import { motion } from "motion/react";

const providers = [
  { name: "Claude", color: "#D4A574" },
  { name: "OpenAI", color: "#10A37F" },
  { name: "Gemini", color: "#4285F4" },
  { name: "Copilot", color: "#6366F1" },
  { name: "Ollama", color: "#FFFFFF" },
];

export default function Providers() {
  return (
    <section className="relative px-6 py-16">
      <div className="mx-auto max-w-[1200px]">
        <div className="border-y border-border-subtle py-10">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-10"
          >
            <span className="text-text-muted text-sm">
              Works with any LLM — or none at all
            </span>

            <div className="flex flex-wrap items-center justify-center gap-3">
              {providers.map((provider, i) => (
                <motion.div
                  key={provider.name}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                  className="flex items-center gap-2 px-4 py-2 rounded-full border border-border-subtle bg-bg-card/30"
                >
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: provider.color }}
                  />
                  <span className="text-sm text-text-muted">
                    {provider.name}
                  </span>
                </motion.div>
              ))}

              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-green/20 bg-green/5">
                <div className="w-1.5 h-1.5 rounded-full bg-green" />
                <span className="text-xs text-green font-medium">
                  Free · Offline
                </span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
