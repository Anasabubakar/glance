"use client";

import { useRef } from "react";
import { motion } from "motion/react";
import { EyeIcon, MousePointerClick01Icon, ActivityIcon, Dashboard01Icon } from "@animateicons/react/huge";
import type { IconHandle } from "@animateicons/react";

const features = [
  {
    icon: EyeIcon,
    title: "Sees your screen",
    description:
      "Real-time screen understanding. Glance watches what you see and builds context from your active windows, text, and UI elements.",
    accent: "bg-indigo",
    wide: true,
  },
  {
    icon: MousePointerClick01Icon,
    title: "Points at things",
    description:
      "A cursor companion that visually highlights exactly what it's referring to — no guessing where to look.",
    accent: "bg-violet",
    wide: false,
  },
  {
    icon: ActivityIcon,
    title: "Acts on them",
    description:
      "Goes beyond suggestions. Glance can click, type, scroll, and navigate your desktop on your behalf.",
    accent: "bg-green",
    wide: false,
  },
  {
    icon: Dashboard01Icon,
    title: "Remembers you",
    description:
      "Learns your preferences, workflows, and habits over time. Each session is smarter than the last.",
    accent: "bg-orange",
    wide: true,
  },
];

function FeatureCard({ feature, index }: { feature: typeof features[number]; index: number }) {
  const iconRef = useRef<IconHandle>(null);

  return (
    <motion.div
      key={feature.title}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className={`relative rounded-2xl border border-border-subtle bg-bg-card/50 p-6 md:p-8 overflow-hidden group hover:border-border-medium transition-colors ${
        feature.wide ? "md:col-span-2" : "md:col-span-1"
      }`}
      onMouseEnter={() => iconRef.current?.startAnimation()}
      onMouseLeave={() => iconRef.current?.stopAnimation()}
    >
      <div
        className={`absolute top-0 left-8 right-8 h-[2px] ${feature.accent} opacity-40 rounded-b-full`}
      />

      <div className="mb-4">
        <feature.icon ref={iconRef} size={32} className="text-text-primary" />
      </div>
      <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
      <p className="text-text-muted text-sm leading-relaxed max-w-md">
        {feature.description}
      </p>
    </motion.div>
  );
}

export default function FeaturesBento() {
  return (
    <section id="features" className="relative px-6 py-24 md:py-32">
      <div className="mx-auto max-w-[1200px]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="font-grotesk text-[11px] font-medium uppercase tracking-[0.2em] text-indigo mb-4 block">
            Capabilities
          </span>
          <h2 className="font-serif italic text-3xl sm:text-4xl md:text-[44px] leading-tight">
            See. Point. Act. Remember.
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {features.map((feature, i) => (
            <FeatureCard key={feature.title} feature={feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
