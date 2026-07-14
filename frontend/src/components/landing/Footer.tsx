import Image from "next/image";
import Link from "next/link";

const columns = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "#features" },
      { label: "Download", href: "#download" },
      { label: "Changelog", href: "/docs/changelog" },
      { label: "Roadmap", href: "/docs/roadmap" },
    ],
  },
  {
    title: "Developer",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "Architecture", href: "/docs/architecture" },
      { label: "Contributing", href: "/docs/contributing" },
      { label: "GitHub", href: "https://github.com/Anasabubakar/glance", external: true },
    ],
  },
  {
    title: "Community",
    links: [
      { label: "X / Twitter", href: "https://x.com/Anas_Abubakar70", external: true },
      { label: "Issues", href: "https://github.com/Anasabubakar/glance/issues", external: true },
      { label: "Discussions", href: "https://github.com/Anasabubakar/glance/discussions", external: true },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="relative border-t border-border-subtle bg-bg-surface/50">
      <div className="mx-auto max-w-[1200px] px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-12">
          <div className="md:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4">
              <Image
                src="/glance-flat.png"
                alt="Glance"
                width={36}
                height={36}
              />
              <span className="text-xl font-semibold tracking-tight">
                Glance
              </span>
            </Link>
            <p className="text-text-muted text-sm leading-relaxed max-w-xs">
              Your intelligent cursor. A voice-first AI companion that sees your
              screen and acts on it.
            </p>
          </div>

          {columns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold mb-4 text-text-primary">
                {col.title}
              </h4>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      {...("external" in link && link.external
                        ? { target: "_blank", rel: "noopener noreferrer" }
                        : {})}
                      className="text-sm text-text-muted hover:text-text-primary transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-8 border-t border-border-subtle">
          <p className="text-text-dim text-xs text-center">
            © 2026 Glance · MIT License · Built by Anas Abubakar
          </p>
        </div>
      </div>
    </footer>
  );
}
