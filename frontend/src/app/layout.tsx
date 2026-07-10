import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Glance - Talk to Your Computer",
  description:
    "Voice-first AI desktop companion for Windows and Linux. She sees your screen, points at things, and actually does them.",
  keywords: [
    "AI",
    "desktop companion",
    "voice assistant",
    "computer use",
    "screen reader",
    "automation",
  ],
  openGraph: {
    title: "Glance - Talk to Your Computer",
    description:
      "Voice-first AI desktop companion. She sees your screen, points at things, and actually does them.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
    >
      <body className="min-h-[100dvh] flex flex-col bg-bg-primary text-text-primary">
        {children}
      </body>
    </html>
  );
}
