import Link from "next/link";
import { docSections } from "@/lib/docs";

export default function DocsHome() {
  return (
    <article className="prose-docs">
      <div className="mb-2">
        <span className="text-[11px] font-grotesk font-medium uppercase tracking-[0.15em] text-indigo">
          Getting Started
        </span>
      </div>
      <h1 className="text-3xl font-bold mb-2">Introduction</h1>
      <p className="text-text-muted text-lg mb-8">
        Glance is a voice-first AI desktop companion that sees your screen, points at
        things, and acts on them. This documentation covers installation, core
        concepts, and practical guides.
      </p>

      <div className="grid gap-8">
        {docSections.map((section) => (
          <div key={section.slug}>
            <h2 className="text-lg font-semibold mb-3 text-text-primary">{section.title}</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {section.items
                .filter((i) => i.slug !== "introduction")
                .map((item) => (
                  <Link
                    key={item.slug}
                    href={item.slug === "introduction" ? "/docs" : `/docs/${item.slug}`}
                    className="block rounded-xl border border-border-subtle bg-bg-card/50 p-4 hover:border-border-medium transition-colors"
                  >
                    <span className="block text-sm font-medium text-text-primary">{item.title}</span>
                    {item.description && (
                      <span className="block text-xs text-text-muted mt-1">{item.description}</span>
                    )}
                  </Link>
                ))}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
