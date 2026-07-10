"use client";

import React from "react";
import { GithubLogo, TwitterLogo, FileText } from "@phosphor-icons/react";

export default function Footer() {
  return (
    <footer className="py-12 px-6 md:px-12 border-t border-white/5 bg-zinc-950">
      <div className="max-w-7xl mx-auto flex flex-col items-center gap-8 text-center">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-blue-600 rounded-full" />
          <span className="text-white font-bold tracking-tight text-sm">Glance</span>
        </div>
        
        <p className="text-zinc-500 text-xs max-w-xs leading-relaxed">
          An open-source AI companion for the modern desktop. <br />
          Built for speed, trust, and agency.
        </p>

        <div className="flex items-center gap-6 text-zinc-500">
          <a href="https://github.com/Anasabubakar/glance" className="hover:text-white transition-colors">
            <GithubLogo size={20} />
          </a>
          <a href="#" className="hover:text-white transition-colors">
            <TwitterLogo size={20} />
          </a>
          <a href="#" className="hover:text-white transition-colors">
            <FileText size={20} />
          </a>
        </div>

        <div className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest">
          © 2026 Glance Project. MIT License.
        </div>
      </div>
    </footer>
  );
}
