"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import clsx from "clsx";
import { docSections } from "@/lib/docs";
import { ChevronRightIcon } from "@animateicons/react/huge";

interface DocsSidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function DocsSidebar({ open, onClose }: DocsSidebarProps) {
  const pathname = usePathname();
  const currentSlug = pathname.replace("/docs/", "").replace("/docs", "");

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          "fixed top-0 left-0 z-50 h-dvh w-72 bg-bg-surface border-r border-border-subtle overflow-y-auto scrollbar-thin transition-transform duration-300 lg:sticky lg:top-0 lg:translate-x-0 lg:z-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between px-5 h-16 border-b border-border-subtle">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/glance-flat.png" alt="Glance" width={24} height={24} />
            <span className="font-semibold text-sm">Glance Docs</span>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1 text-text-muted hover:text-text-primary"
            aria-label="Close sidebar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>

        <nav className="p-4">
          {docSections.map((section) => (
            <div key={section.slug} className="mb-6">
              <h4 className="text-[11px] font-grotesk font-medium uppercase tracking-[0.15em] text-text-dim mb-2 px-2">
                {section.title}
              </h4>
              <ul className="space-y-0.5">
                {section.items.map((item) => {
                  const active =
                    currentSlug === item.slug ||
                    (currentSlug === "" && item.slug === "introduction");
                  return (
                    <li key={item.slug}>
                      <Link
                        href={
                          item.slug === "introduction"
                            ? "/docs"
                            : `/docs/${item.slug}`
                        }
                        onClick={onClose}
                        className={clsx(
                          "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
                          active
                            ? "bg-indigo/10 text-indigo font-medium"
                            : "text-text-muted hover:text-text-primary hover:bg-bg-card/50"
                        )}
                      >
                        {active && <ChevronRightIcon size={12} />}
                        {item.title}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
