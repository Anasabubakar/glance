import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Instrument_Serif, Space_Grotesk } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: "400",
  style: "italic",
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["500"],
});

export const metadata: Metadata = {
  title: "Glance — Your Intelligent Cursor",
  description:
    "Voice-first AI desktop companion for Windows and Linux. It sees your screen, points at things, and actually does them.",
  icons: {
    icon: "/glance-flat.png",
    apple: "/glance-flat.png",
  },
  keywords: [
    "AI",
    "desktop companion",
    "voice assistant",
    "computer use",
    "screen reader",
    "automation",
    "cursor",
    "Glance",
  ],
  openGraph: {
    title: "Glance — Your Intelligent Cursor",
    description:
      "Voice-first AI desktop companion. It sees your screen, points at things, and actually does them.",
    type: "website",
  },
};
