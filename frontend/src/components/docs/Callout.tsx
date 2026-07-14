"use client";

import clsx from "clsx";
import { NotificationIcon, ActivityIcon, EyeIcon } from "@animateicons/react/huge";

interface CalloutProps {
  type?: "info" | "warning" | "tip" | "danger";
  title?: string;
  children: React.ReactNode;
}

function InfoSvg({ className }: { className?: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
    </svg>
  );
}

function WarningSvg({ className }: { className?: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
    </svg>
  );
}

function DangerSvg({ className }: { className?: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
    </svg>
  );
}

const icons = {
  info: InfoSvg,
  warning: WarningSvg,
  tip: ActivityIcon,
  danger: DangerSvg,
};

const styles = {
  info: "border-blue-glow/20 bg-blue-glow/5",
  warning: "border-orange/20 bg-orange/5",
  tip: "border-green/20 bg-green/5",
  danger: "border-red-500/20 bg-red-500/5",
};

const iconColors = {
  info: "text-blue-glow",
  warning: "text-orange",
  tip: "text-green",
  danger: "text-red-400",
};

export default function Callout({
  type = "info",
  title,
  children,
}: CalloutProps) {
  const Icon = icons[type];

  return (
    <div
      className={clsx(
        "rounded-xl border p-4 my-4 flex gap-3",
        styles[type]
      )}
    >
      <Icon size={20} className={clsx("shrink-0 mt-0.5", iconColors[type])} />
      <div>
        {title && (
          <p className="text-sm font-semibold mb-1 text-text-primary">
            {title}
          </p>
        )}
        <div className="text-sm text-text-muted leading-relaxed">
          {children}
        </div>
      </div>
    </div>
  );
}
