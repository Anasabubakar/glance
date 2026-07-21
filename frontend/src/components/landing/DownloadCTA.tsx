"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { DownloadIcon } from "@animateicons/react/huge";
import clsx from "clsx";

interface DownloadFile {
  label: string;
  ext: string;
  size: string;
  href: string;
}

interface Release {
  version: string;
  tag: string;
  label: string;
  files: Record<string, DownloadFile[]>;
}

const RELEASES: Release[] = [
  {
    version: "v0.2.0",
    tag: "v0.2.0",
    label: "Latest",
    files: {
      Windows: [
        { label: "Installer", ext: ".exe", size: "~85 MB", href: "https://github.com/Anasabubakar/glance/releases/download/v0.2.0/Setup-Glance.exe" },
      ],
      Linux: [
        { label: "Package (Debian/Ubuntu)", ext: ".deb", size: "~80 MB", href: "https://github.com/Anasabubakar/glance/releases/download/v0.2.0/glance_0.2.0_amd64.deb" },
        { label: "AppImage (any distro)", ext: ".AppImage", size: "~80 MB", href: "https://github.com/Anasabubakar/glance/releases/download/v0.2.0/Glance-0.2.0-x86_64.AppImage" },
      ],
    },
  },
  {
    version: "v0.1.0",
    tag: "v0.1.0",
    label: "Previous",
    files: {
      Windows: [
        { label: "Installer", ext: ".exe", size: "~80 MB", href: "https://github.com/Anasabubakar/glance/releases/download/v0.1.0/Setup-Glance.exe" },
      ],
      Linux: [
        { label: "Package (Debian/Ubuntu)", ext: ".deb", size: "~75 MB", href: "https://github.com/Anasabubakar/glance/releases/download/v0.1.0/glance_0.1.0_amd64.deb" },
        { label: "AppImage (any distro)", ext: ".AppImage", size: "~75 MB", href: "https://github.com/Anasabubakar/glance/releases/download/v0.1.0/Glance-0.1.0-x86_64.AppImage" },
      ],
    },
  },
];

function PlatformIcon({ name, className }: { name: string; className?: string }) {
  if (name === "Windows") {
    return (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" className={className}>
        <path d="M3 5.548l7.051-.967v6.797H3V5.548zm0 12.904l7.051.967v-6.797H3v5.83zm7.86 1.077L21 21V12.622h-10.14v6.907zm0-14.058v6.907H21V3l-10.14 1.471z"/>
      </svg>
    );
  }
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12.504 0c-.155 0-.315.008-.48.021-4.226.333-3.105 4.807-3.17 6.298-.076 1.092-.3 1.953-1.05 3.02-.885 1.051-2.127 2.75-2.716 4.521-.278.832-.41 1.684-.287 2.489a.424.424 0 00-.11.135c-.26.268-.45.6-.663.839-.199.199-.485.267-.797.4-.313.136-.658.269-.864.68-.09.189-.136.394-.132.602 0 .199.027.4.055.536.058.399.116.728.04.97-.249.68-.28 1.145-.106 1.484.174.334.535.47.94.601.81.2 1.91.135 2.774.6.926.466 1.866.67 2.616.47.526-.116.97-.464 1.208-.946.587-.003 1.23-.269 2.26-.334.699-.058 1.574.267 2.577.2.025.134.063.198.114.333l.003.003c.391.778 1.113 1.022 1.903 1.395.199.093.387.135.602.2.698.2 1.553.465 2.378.065.264-.13.468-.324.596-.548.348-.6.185-1.347-.19-1.886-.25-.36-.55-.723-.862-1.012-.065-.06-.12-.133-.16-.217-.053-.12-.072-.27-.04-.415.03-.145.084-.254.147-.376.063-.122.14-.254.18-.39.12-.26.15-.6-.022-.88-.06-.1-.164-.197-.283-.2l-.005-.007c-.014-.003-.027-.003-.04-.003-.072 0-.147.012-.217.03-.252.066-.467.18-.67.267-.14.065-.28.133-.432.133a.627.627 0 01-.258-.043c-.4-.175-.715-.52-.948-.827-.067-.088-.133-.18-.2-.27-.266-.348-.473-.817-.608-1.399-.073-.33-.12-.68-.133-1.026-.014-.315.04-.624.15-.933.113-.318.26-.635.34-.98.078-.333.09-.668.026-1.003a3.276 3.276 0 00-.14-.504c-.083-.228-.18-.44-.28-.64-.097-.2-.196-.386-.292-.565-.092-.176-.183-.338-.265-.487a5.082 5.082 0 01-.163-.32c-.062-.134-.106-.27-.135-.406-.03-.12-.05-.266-.016-.4.027-.136.079-.233.158-.317.076-.084.173-.14.267-.173.377-.14.773-.02 1.143-.02.266 0 .515-.156.64-.377.042-.076.078-.16.096-.25.064-.312-.062-.638-.292-.865a1.52 1.52 0 00-.328-.217c-.147-.087-.318-.152-.464-.248-.324-.216-.55-.643-.558-1.12-.002-.266.1-.498.252-.69.153-.19.35-.333.568-.44a3.2 3.2 0 011.256-.39 3.381 3.381 0 01.64.003c.28.036.562.105.831.232.21.1.4.234.527.4.128.165.198.37.198.58 0 .106-.024.208-.05.306a2.067 2.067 0 01-.166.44c-.05.09-.096.177-.124.268-.024.074-.04.16-.024.24.012.066.043.12.08.17.106.13.274.175.47.145.196-.03.355-.12.514-.224.228-.148.455-.31.648-.504.192-.193.35-.4.488-.628.136-.228.24-.476.298-.73.052-.22.08-.448.05-.667-.026-.206-.087-.406-.164-.595-.168-.408-.44-.765-.795-1.041-.174-.135-.366-.244-.564-.32a4.681 4.681 0 00-1.176-.32c-.36-.065-.724-.092-1.086-.1l-.018.002c.008.046.002.092-.016.136-.003.007-.002.014-.004.02-.01.033-.026.064-.038.098-.028.08-.056.16-.08.24-.082.28-.16.565-.198.86-.018.148-.027.3-.023.45.003.314.05.626.107.934z"/>
    </svg>
  );
}

export default function DownloadCTA() {
  const [activeVersion, setActiveVersion] = useState(0);
  const [showAllVersions, setShowAllVersions] = useState(false);
  const release = RELEASES[activeVersion];

  return (
    <section id="download" className="relative px-6 py-24 md:py-32">
      <div className="mx-auto max-w-[1200px]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="font-grotesk text-[11px] font-medium uppercase tracking-[0.2em] text-indigo mb-4 block">
            Get Started
          </span>
          <h2 className="font-serif italic text-4xl sm:text-5xl md:text-[56px] leading-tight mb-4">
            Try Glance today.
          </h2>
          <p className="text-text-muted text-base sm:text-lg max-w-md mx-auto">
            Free and open source. MIT licensed. No account required.
          </p>
        </motion.div>

        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 p-1 rounded-xl bg-bg-surface border border-border-subtle">
            {RELEASES.map((r, i) => (
              <button
                key={r.version}
                onClick={() => { setActiveVersion(i); setShowAllVersions(false); }}
                className={clsx(
                  "px-5 py-2 text-sm font-medium rounded-lg transition-all",
                  i === activeVersion && !showAllVersions
                    ? "bg-gradient-brand text-white shadow-md"
                    : "text-text-muted hover:text-text-primary"
                )}
              >
                {r.label}
                <span className="ml-1.5 text-xs opacity-70">{r.version}</span>
              </button>
            ))}
          </div>
        </div>

        {showAllVersions ? (
          <div className="space-y-12 max-w-4xl mx-auto">
            {RELEASES.map((rel, ri) => (
              <motion.div
                key={rel.version}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: ri * 0.1 }}
              >
                <div className="flex items-center gap-3 mb-6">
                  <h3 className="text-lg font-semibold">{rel.version}</h3>
                  <span className="text-xs text-text-dim px-2.5 py-0.5 rounded-full bg-bg-elevated">
                    {rel.label}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  {Object.entries(rel.files).map(([platform, files]) => (
                    <div key={platform}>
                      <div className="flex items-center gap-2 mb-3">
                        <PlatformIcon name={platform} className="w-5 h-5 text-text-muted" />
                        <h4 className="text-sm font-medium text-text-muted">{platform}</h4>
                      </div>
                      <div className="space-y-2">
                        {files.map((file) => (
                          <a
                            key={file.ext}
                            href={file.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl border border-border-subtle bg-bg-card/50 hover:border-border-medium hover:bg-bg-card transition-all group"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <DownloadIcon size={16} className="text-indigo shrink-0" />
                              <div className="min-w-0">
                                <div className="text-sm font-medium truncate">{file.label}</div>
                                <div className="text-xs text-text-dim">{file.ext} · {file.size}</div>
                              </div>
                            </div>
                            <span className="text-xs font-medium text-indigo shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                              Download
                            </span>
                          </a>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl mx-auto">
            {Object.entries(release.files).map(([platform, files], i) => (
              <motion.div
                key={platform}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="rounded-2xl border border-border-subtle bg-bg-card/50 p-6 flex flex-col items-center text-center group hover:border-border-medium transition-colors"
              >
                <PlatformIcon name={platform} className="text-text-primary mb-4" />
                <h3 className="text-lg font-semibold mb-1">{platform}</h3>
                <span className="text-text-dim text-xs mb-4 px-2 py-0.5 rounded-full bg-bg-elevated">
                  {platform === "Windows" ? "10 / 11" : "Ubuntu / Debian / Fedora"}
                </span>

                <div className="w-full space-y-2 mt-1">
                  {files.map((file) => (
                    <a
                      key={file.ext}
                      href={file.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white text-sm font-medium bg-gradient-brand hover:opacity-90 transition-opacity"
                    >
                      <DownloadIcon size={18} />
                      Download {file.ext}
                    </a>
                  ))}
                </div>

                {files.length > 1 && (
                  <div className="mt-3 text-xs text-text-dim">
                    {files.map((f) => f.ext).join(" · ")} available
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="text-center mt-10"
        >
          <button
            onClick={() => setShowAllVersions(!showAllVersions)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border-subtle text-sm text-text-muted hover:text-text-primary hover:border-border-medium transition-all bg-bg-card/30"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={clsx("transition-transform", showAllVersions && "rotate-180")}>
              <path d="M6 9l6 6 6-6"/>
            </svg>
            {showAllVersions ? "Show latest only" : "All versions & formats"}
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="text-center mt-12"
        >
          <a
            href="https://github.com/Anasabubakar/glance/releases"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-text-muted hover:text-text-primary underline underline-offset-4 decoration-border-medium transition-colors"
          >
            View all releases on GitHub →
          </a>
        </motion.div>
      </div>
    </section>
  );
}
