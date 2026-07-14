export interface DocSection {
  title: string;
  slug: string;
  items: DocItem[];
}

export interface DocItem {
  title: string;
  slug: string;
  description?: string;
}

export const docSections: DocSection[] = [
  {
    title: "Getting Started",
    slug: "getting-started",
    items: [
      { title: "Introduction", slug: "introduction", description: "What is Glance and why it exists" },
      { title: "Installation", slug: "installation", description: "Download and install Glance on Windows or Linux" },
      { title: "Quick Start", slug: "quick-start", description: "Get up and running in 60 seconds" },
    ],
  },
  {
    title: "Core Concepts",
    slug: "core-concepts",
    items: [
      { title: "Features", slug: "features", description: "Everything Glance can do" },
      { title: "Architecture", slug: "architecture", description: "How Glance works under the hood" },
      { title: "Configuration", slug: "configuration", description: "Customize Glance to your workflow" },
    ],
  },
  {
    title: "Guides",
    slug: "guides",
    items: [
      { title: "Voice Commands", slug: "voice-commands", description: "How to talk to Glance" },
      { title: "LLM Providers", slug: "llm-providers", description: "Set up Claude, OpenAI, Gemini, or local models" },
      { title: "Keyboard Shortcuts", slug: "keyboard-shortcuts", description: "All keyboard shortcuts and hotkeys" },
    ],
  },
  {
    title: "Resources",
    slug: "resources",
    items: [
      { title: "FAQ", slug: "faq", description: "Frequently asked questions" },
      { title: "Troubleshooting", slug: "troubleshooting", description: "Common issues and fixes" },
      { title: "Changelog", slug: "changelog", description: "Release notes and version history" },
      { title: "Roadmap", slug: "roadmap", description: "What's coming next" },
      { title: "Contributing", slug: "contributing", description: "How to contribute to Glance" },
    ],
  },
];

export function getAllDocSlugs(): string[] {
  return docSections.flatMap((section) => section.items.map((item) => item.slug));
}

export function getDocBySlug(slug: string): { item: DocItem; section: DocSection } | null {
  for (const section of docSections) {
    const item = section.items.find((i) => i.slug === slug);
    if (item) return { item, section };
  }
  return null;
}

export function getAdjacentDocs(slug: string): { prev: DocItem | null; next: DocItem | null } {
  const allItems = docSections.flatMap((s) => s.items);
  const idx = allItems.findIndex((i) => i.slug === slug);
  return {
    prev: idx > 0 ? allItems[idx - 1] : null,
    next: idx < allItems.length - 1 ? allItems[idx + 1] : null,
  };
}
