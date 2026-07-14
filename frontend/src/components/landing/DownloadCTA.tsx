"use client";

import { motion } from "motion/react";
import { DownloadIcon } from "@animateicons/react/huge";

function WindowsIcon({ className }: { className?: string }) {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M3 5.548l7.051-.967v6.797H3V5.548zm0 12.904l7.051.967v-6.797H3v5.83zm7.86 1.077L21 21V12.622h-10.14v6.907zm0-14.058v6.907H21V3l-10.14 1.471z"/>
    </svg>
  );
}

function LinuxIcon({ className }: { className?: string }) {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12.504 0c-.155 0-.315.008-.48.021-4.226.333-3.105 4.807-3.17 6.298-.076 1.092-.3 1.953-1.05 3.02-.885 1.051-2.127 2.75-2.716 4.521-.278.832-.41 1.684-.287 2.489a.424.424 0 00-.11.135c-.26.268-.45.6-.663.839-.199.199-.485.267-.797.4-.313.136-.658.269-.864.68-.09.189-.136.394-.132.602 0 .199.027.4.055.536.058.399.116.728.04.97-.249.68-.28 1.145-.106 1.484.174.334.535.47.94.601.81.2 1.91.135 2.774.6.926.466 1.866.67 2.616.47.526-.116.97-.464 1.208-.946.587-.003 1.23-.269 2.26-.334.699-.058 1.574.267 2.577.2.025.134.063.198.114.333l.003.003c.391.778 1.113 1.022 1.903 1.395.199.093.387.135.602.2.698.2 1.553.465 2.378.065.264-.13.468-.324.596-.548.348-.6.185-1.347-.19-1.886-.25-.36-.55-.723-.862-1.012-.065-.06-.12-.133-.16-.217-.053-.12-.072-.27-.04-.415.03-.145.084-.254.147-.376.063-.122.14-.254.18-.39.12-.26.15-.6-.022-.88-.06-.1-.164-.197-.283-.2l-.005-.007c-.014-.003-.027-.003-.04-.003-.072 0-.147.012-.217.03-.252.066-.467.18-.67.267-.14.065-.28.133-.432.133a.627.627 0 01-.258-.043c-.4-.175-.715-.52-.948-.827-.067-.088-.133-.18-.2-.27-.266-.348-.473-.817-.608-1.399-.073-.33-.12-.68-.133-1.026-.014-.315.04-.624.15-.933.113-.318.26-.635.34-.98.078-.333.09-.668.026-1.003a3.276 3.276 0 00-.14-.504c-.083-.228-.18-.44-.28-.64-.097-.2-.196-.386-.292-.565-.092-.176-.183-.338-.265-.487a5.082 5.082 0 01-.163-.32c-.062-.134-.106-.27-.135-.406-.03-.12-.05-.266-.016-.4.027-.136.079-.233.158-.317.076-.084.173-.14.267-.173.377-.14.773-.02 1.143-.02.266 0 .515-.156.64-.377.042-.076.078-.16.096-.25.064-.312-.062-.638-.292-.865a1.52 1.52 0 00-.328-.217c-.147-.087-.318-.152-.464-.248-.324-.216-.55-.643-.558-1.12-.002-.266.1-.498.252-.69.153-.19.35-.333.568-.44a3.2 3.2 0 011.256-.39 3.381 3.381 0 01.64.003c.28.036.562.105.831.232.21.1.4.234.527.4.128.165.198.37.198.58 0 .106-.024.208-.05.306a2.067 2.067 0 01-.166.44c-.05.09-.096.177-.124.268-.024.074-.04.16-.024.24.012.066.043.12.08.17.106.13.274.175.47.145.196-.03.355-.12.514-.224.228-.148.455-.31.648-.504.192-.193.35-.403.467-.622.12-.22.2-.447.234-.674.06-.4-.04-.768-.254-1.07-.215-.3-.53-.506-.88-.632a4.25 4.25 0 00-1.194-.265 6.043 6.043 0 00-1.32.052 5.273 5.273 0 00-1.16.352 3.84 3.84 0 00-.99.6c-.291.25-.537.555-.72.905-.09.17-.16.348-.2.533-.044.182-.058.37-.035.56.024.186.08.373.16.55.082.182.186.35.308.505.123.155.262.29.414.4.15.108.312.19.484.243.172.054.352.074.532.062.182-.012.358-.058.525-.13.164-.072.317-.17.457-.29a4.37 4.37 0 00.369-.38c.1-.115.196-.242.276-.374.08-.127.15-.263.2-.402.054-.138.09-.28.102-.42.012-.147.002-.293-.035-.433-.038-.136-.098-.263-.177-.378-.152-.22-.37-.38-.616-.475a2.12 2.12 0 00-.757-.15z"/>
    </svg>
  );
}

const platforms = [
  {
    name: "Windows",
    icon: WindowsIcon,
    version: "10 / 11",
    method: "Installer",
    extension: ".exe",
    size: "~85 MB",
    color: "bg-blue-glow",
    href: "https://github.com/Anasabubakar/glance/releases/latest/download/Setup-Glance.exe",
  },
  {
    name: "Linux",
    icon: LinuxIcon,
    version: "Ubuntu / Debian",
    method: "Package",
    extension: ".deb",
    size: "~80 MB",
    color: "bg-orange",
    href: "https://github.com/Anasabubakar/glance/releases/latest/download/glance_0.1.0_amd64.deb",
  },
];

export default function DownloadCTA() {
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {platforms.map((platform, i) => (
            <motion.div
              key={platform.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="rounded-2xl border border-border-subtle bg-bg-card/50 p-6 flex flex-col items-center text-center group hover:border-border-medium transition-colors"
            >
              <platform.icon className="text-text-primary mb-4" />
              <h3 className="text-lg font-semibold mb-1">{platform.name}</h3>
              <span className="text-text-dim text-xs mb-4 px-2 py-0.5 rounded-full bg-bg-elevated">
                {platform.version}
              </span>

              <div className="text-text-muted text-sm mb-1">
                {platform.method} · {platform.extension}
              </div>
              <div className="text-text-dim text-xs mb-6">{platform.size}</div>

              <a
                href={platform.href}
                target="_blank"
                rel="noopener noreferrer"
                className={`w-full inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white text-sm font-medium ${platform.color} hover:opacity-90 transition-opacity`}
              >
                <DownloadIcon size={18} />
                Download
              </a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
