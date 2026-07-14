"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { SearchIcon } from "@animateicons/react/huge";
import clsx from "clsx";
import { docSections } from "@/lib/docs";

interface SearchDialogProps {
  open: boolean;
  onClose: () => void;
}

const allDocs = docSections.flatMap((section) =>
  section.items.map((item) => ({
    ...item,
    section: section.title,
    href: item.slug === "introduction" ? "/docs" : `/docs/${item.slug}`,
  }))
);

export default function SearchDialog({ open, onClose }: SearchDialogProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();

  const results = query.trim()
    ? allDocs.filter(
        (doc) =>
          doc.title.toLowerCase().includes(query.toLowerCase()) ||
          doc.description?.toLowerCase().includes(query.toLowerCase()) ||
          doc.section.toLowerCase().includes(query.toLowerCase())
      )
    : allDocs;

  const navigate = useCallback(
    (href: string) => {
      router.push(href);
      onClose();
      setQuery("");
    },
    [router, onClose]
  );

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelectedIndex(0);
  }, [open]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (open) onClose();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && results[selectedIndex]) {
        e.preventDefault();
        navigate(results[selectedIndex].href);
      } else if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, results, selectedIndex, navigate, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" role="dialog" aria-modal="true" aria-label="Search documentation">
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-lg mx-4 rounded-2xl border border-border-subtle bg-bg-surface shadow-2xl shadow-black/40 overflow-hidden">
        <div className="flex items-center gap-3 px-4 border-b border-border-subtle">
          <SearchIcon size={18} className="text-text-dim shrink-0" />
          <input
            type="text"
            placeholder="Search documentation..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            autoFocus
            className="flex-1 py-3.5 bg-transparent text-sm text-text-primary placeholder:text-text-dim outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 text-text-dim hover:text-text-primary"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto scrollbar-thin p-2">
          {results.length === 0 ? (
            <div className="py-8 text-center text-sm text-text-dim">
              No results found
            </div>
          ) : (
            results.map((doc, i) => (
              <button
                key={doc.slug}
                onClick={() => navigate(doc.href)}
                className={clsx(
                  "w-full flex flex-col gap-0.5 px-3 py-2.5 rounded-lg text-left transition-colors",
                  i === selectedIndex
                    ? "bg-indigo/10 text-text-primary"
                    : "text-text-muted hover:bg-bg-card/50"
                )}
              >
                <span className="text-sm font-medium">{doc.title}</span>
                {doc.description && (
                  <span className="text-xs text-text-dim line-clamp-1">
                    {doc.description}
                  </span>
                )}
              </button>
            ))
          )}
        </div>

        <div className="flex items-center gap-4 px-4 py-2.5 border-t border-border-subtle text-[10px] text-text-dim">
          <span>↑↓ Navigate</span>
          <span>↵ Open</span>
          <span>Esc Close</span>
        </div>
      </div>
    </div>
  );
}
