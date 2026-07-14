"use client";

import { useState } from "react";
import { CopyIcon, CheckIcon } from "@animateicons/react/huge";

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
}

export default function CodeBlock({
  code,
  language = "bash",
  filename,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-border-subtle bg-bg-card/50 overflow-hidden my-4">
      {filename && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-border-subtle bg-bg-surface/50">
          <span className="text-xs text-text-dim font-mono">{filename}</span>
          <span className="text-[10px] text-text-dim uppercase tracking-wider">
            {language}
          </span>
        </div>
      )}
      <div className="relative group">
        <pre className="p-4 overflow-x-auto text-sm font-mono leading-relaxed text-text-muted">
          <code>{code}</code>
        </pre>
        <button
          onClick={handleCopy}
          className="absolute top-3 right-3 p-1.5 rounded-md bg-bg-elevated border border-border-subtle text-text-dim hover:text-text-primary opacity-0 group-hover:opacity-100 transition-all"
          aria-label="Copy code"
        >
          {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
        </button>
      </div>
    </div>
  );
}
