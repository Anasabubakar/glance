"use client";

import Link from "next/link";
import { Menu01Icon, SearchIcon, ChevronRightIcon } from "@animateicons/react/huge";

interface DocsHeaderProps {
  breadcrumbs: { label: string; href?: string }[];
  onMenuClick: () => void;
  onSearchClick: () => void;
}

export default function DocsHeader({
  breadcrumbs,
  onMenuClick,
  onSearchClick,
}: DocsHeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-6 h-14 border-b border-border-subtle glass">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-1.5 text-text-muted hover:text-text-primary"
          aria-label="Open sidebar"
        >
          <Menu01Icon size={20} />
        </button>

        <nav className="flex items-center gap-1.5 text-sm">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <ChevronRightIcon size={10} className="text-text-dim" />}
              {crumb.href ? (
                <Link
                  href={crumb.href}
                  className="text-text-muted hover:text-text-primary transition-colors"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-text-primary font-medium">
                  {crumb.label}
                </span>
              )}
            </span>
          ))}
        </nav>
      </div>

      <button
        onClick={onSearchClick}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border-subtle bg-bg-card/30 text-text-dim text-sm hover:border-border-medium transition-colors"
      >
        <SearchIcon size={14} />
        <span className="hidden sm:inline">Search docs...</span>
        <kbd className="hidden sm:inline px-1.5 py-0.5 rounded text-[10px] font-mono bg-bg-elevated border border-border-subtle">
          ⌘K
        </kbd>
      </button>
    </header>
  );
}
