"use client";

import Link from "next/link";
import { ChevronRightIcon } from "@animateicons/react/huge";
import type { DocItem } from "@/lib/docs";

interface DocsPaginationProps {
  prev: DocItem | null;
  next: DocItem | null;
}

export default function DocsPagination({ prev, next }: DocsPaginationProps) {
  return (
    <div className="flex items-center justify-between mt-16 pt-8 border-t border-border-subtle">
      {prev ? (
        <Link
          href={prev.slug === "introduction" ? "/docs" : `/docs/${prev.slug}`}
          className="group flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors"
        >
          <span className="rotate-180 group-hover:-translate-x-0.5 transition-transform inline-flex">
            <ChevronRightIcon size={14} />
          </span>
          {prev.title}
        </Link>
      ) : (
        <div />
      )}
      {next ? (
        <Link
          href={`/docs/${next.slug}`}
          className="group flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors"
        >
          {next.title}
          <span className="group-hover:translate-x-0.5 transition-transform inline-flex">
            <ChevronRightIcon size={14} />
          </span>
        </Link>
      ) : (
        <div />
      )}
    </div>
  );
}
