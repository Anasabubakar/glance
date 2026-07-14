"use client";

import clsx from "clsx";

interface TOCItem {
  id: string;
  text: string;
  level: number;
}

interface DocsTOCProps {
  items: TOCItem[];
  activeId?: string;
}

export default function DocsTOC({ items, activeId }: DocsTOCProps) {
  if (items.length === 0) return null;

  return (
    <aside className="hidden xl:block w-56 shrink-0">
      <div className="sticky top-20">
        <h4 className="text-[11px] font-grotesk font-medium uppercase tracking-[0.15em] text-text-dim mb-3">
          On this page
        </h4>
        <ul className="space-y-1.5">
          {items.map((item) => (
            <li key={item.id}>
              <a
                href={`#${item.id}`}
                className={clsx(
                  "block text-sm transition-colors",
                  item.level > 2 && "pl-3",
                  activeId === item.id
                    ? "text-indigo font-medium"
                    : "text-text-muted hover:text-text-primary"
                )}
              >
                {item.text}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
