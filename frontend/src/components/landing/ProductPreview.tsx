"use client";

import Image from "next/image";
import { motion } from "motion/react";

export default function ProductPreview() {
  return (
    <section className="relative px-6 pb-24">
      <div className="mx-auto max-w-[1200px]">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="relative rounded-2xl border border-border-subtle bg-bg-surface overflow-hidden shadow-2xl shadow-black/40"
        >
          <div className="flex items-center gap-2 px-5 py-3.5 border-b border-border-subtle bg-bg-card/50">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#FF5F57]" />
              <div className="w-3 h-3 rounded-full bg-[#FFBD2E]" />
              <div className="w-3 h-3 rounded-full bg-[#28CA41]" />
            </div>
            <span className="text-xs text-text-dim ml-3 font-mono">
              My Dashboard — Chrome
            </span>
          </div>

          <div className="flex min-h-[500px] md:min-h-[600px]">
            <div className="hidden md:flex w-56 flex-col border-r border-border-subtle bg-bg-card/30 p-4 gap-1">
              {["Dashboard", "Settings", "Profile", "Analytics", "Billing"].map(
                (item, i) => (
                  <div
                    key={item}
                    className={`px-3 py-2 rounded-lg text-sm ${
                      i === 1
                        ? "bg-indigo/10 text-indigo font-medium"
                        : "text-text-muted hover:text-text-primary"
                    }`}
                  >
                    {item}
                  </div>
                )
              )}
            </div>

            <div className="flex-1 p-6 md:p-8">
              <h3 className="text-xl font-semibold mb-1">Settings</h3>
              <p className="text-text-muted text-sm mb-8">
                Manage your account preferences
              </p>

              <div className="space-y-5">
                <div className="rounded-xl border border-border-subtle bg-bg-card/40 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium">Notifications</span>
                    <div className="w-10 h-5 rounded-full bg-indigo relative">
                      <div className="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-white" />
                    </div>
                  </div>
                  <p className="text-text-dim text-xs">
                    Receive email notifications for updates
                  </p>
                </div>

                <div className="rounded-xl border border-border-subtle bg-bg-card/40 p-5">
                  <span className="text-sm font-medium block mb-3">Theme</span>
                  <div className="flex gap-2">
                    {["Light", "Dark", "System"].map((t, i) => (
                      <div
                        key={t}
                        className={`px-4 py-1.5 rounded-lg text-xs font-medium ${
                          i === 1
                            ? "bg-indigo text-white"
                            : "bg-bg-elevated text-text-muted"
                        }`}
                      >
                        {t}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-border-subtle bg-bg-card/40 p-5">
                  <span className="text-sm font-medium block mb-3">
                    Language
                  </span>
                  <div className="flex items-center justify-between px-4 py-2.5 rounded-lg bg-bg-elevated text-sm text-text-muted">
                    <span>English (US)</span>
                    <span className="text-text-dim">▾</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 mt-8">
                <button className="px-6 py-2.5 rounded-xl bg-gradient-brand text-white text-sm font-medium">
                  Save Changes
                </button>
                <button className="px-6 py-2.5 rounded-xl border border-border-subtle text-text-muted text-sm font-medium">
                  Cancel
                </button>
              </div>
            </div>
          </div>

          <div className="absolute bottom-24 right-16 md:right-24 z-20">
            <Image
              src="/glance-cursor.png"
              alt="Glance cursor buddy"
              width={48}
              height={48}
              className="drop-shadow-lg animate-[float_3s_ease-in-out_infinite]"
              style={{ height: "auto" }}
            />
          </div>

          <motion.div
            initial={{ opacity: 0, x: 20, y: 10 }}
            whileInView={{ opacity: 1, x: 0, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="absolute bottom-36 right-20 md:right-32 z-10 max-w-[280px]"
          >
            <div className="glass-card rounded-xl px-4 py-3 text-sm text-text-primary">
              I see a Save button here. Want me to click it for you?
              <div className="absolute -bottom-1.5 right-6 w-3 h-3 bg-bg-card/60 border-r border-b border-border-subtle rotate-45" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.9 }}
            className="absolute bottom-8 right-20 md:right-32 z-10"
          >
            <div className="flex items-center gap-2 glass-card rounded-full px-4 py-2">
              <div className="w-2 h-2 rounded-full bg-green animate-pulse" />
              <span className="text-xs text-text-muted font-mono">
                &quot;Save my settings&quot;
              </span>
            </div>
          </motion.div>
        </motion.div>
      </div>

    </section>
  );
}
