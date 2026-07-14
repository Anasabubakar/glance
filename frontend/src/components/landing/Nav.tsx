"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import clsx from "clsx";
import { Menu01Icon } from "@animateicons/react/huge";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "How it Works", href: "#how-it-works" },
  { label: "Docs", href: "/docs" },
  { label: "Download", href: "#download" },
  { label: "GitHub", href: "https://github.com/Anasabubakar/glance", external: true },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={clsx(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled ? "glass border-b border-border-subtle" : "bg-transparent"
      )}
    >
      <div className="mx-auto max-w-[1200px] px-6 flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2.5">
          <Image src="/glance-flat.png" alt="Glance" width={32} height={32} />
          <span className="text-lg font-semibold tracking-tight">Glance</span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              {...(link.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
              className="text-sm font-medium text-text-muted hover:text-text-primary transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden md:block">
          <Link
            href="#download"
            className="relative inline-flex items-center px-5 py-2 text-sm font-medium rounded-lg bg-gradient-brand text-white hover:opacity-90 transition-opacity"
          >
            Download
          </Link>
        </div>

        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden p-2 text-text-muted hover:text-text-primary transition-colors"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          ) : (
            <Menu01Icon size={24} />
          )}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden glass border-t border-border-subtle">
          <div className="px-6 py-4 flex flex-col gap-4">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                {...(link.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                onClick={() => setMobileOpen(false)}
                className="text-base font-medium text-text-muted hover:text-text-primary transition-colors"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="#download"
              onClick={() => setMobileOpen(false)}
              className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium rounded-lg bg-gradient-brand text-white"
            >
              Download
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
