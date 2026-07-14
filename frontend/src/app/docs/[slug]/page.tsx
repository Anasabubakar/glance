import { notFound } from "next/navigation";
import { getDocBySlug, getAdjacentDocs, getAllDocSlugs } from "@/lib/docs";
import DocsPagination from "@/components/docs/DocsPagination";
import CodeBlock from "@/components/docs/CodeBlock";
import Callout from "@/components/docs/Callout";

export function generateStaticParams() {
  return getAllDocSlugs()
    .filter((slug) => slug !== "introduction")
    .map((slug) => ({ slug }));
}

const docContent: Record<string, React.ReactNode> = {
  installation: <InstallationContent />,
  "quick-start": <QuickStartContent />,
  features: <FeaturesContent />,
  architecture: <ArchitectureContent />,
  configuration: <ConfigurationContent />,
  "voice-commands": <VoiceCommandsContent />,
  "llm-providers": <LLMProvidersContent />,
  "keyboard-shortcuts": <KeyboardShortcutsContent />,
  faq: <FAQContent />,
  troubleshooting: <TroubleshootingContent />,
  changelog: <ChangelogContent />,
  roadmap: <RoadmapContent />,
  contributing: <ContributingContent />,
};

export default async function DocPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const doc = getDocBySlug(slug);
  if (!doc) notFound();

  const { prev, next } = getAdjacentDocs(slug);
  const Content = docContent[slug];

  return (
    <article className="prose-docs">
      <div className="mb-2">
        <span className="text-[11px] font-grotesk font-medium uppercase tracking-[0.15em] text-indigo">
          {doc.section.title}
        </span>
      </div>
      <h1 className="text-3xl font-bold mb-2">{doc.item.title}</h1>
      {doc.item.description && (
        <p className="text-text-muted text-lg mb-8">{doc.item.description}</p>
      )}
      {Content || (
        <p className="text-text-muted">This page is coming soon.</p>
      )}
      <DocsPagination prev={prev} next={next} />
    </article>
  );
}

function InstallationContent() {
  return (
    <>
      <h2 id="system-requirements" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">System Requirements</h2>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• <strong className="text-text-primary">Windows</strong>: Windows 10 or later (64-bit)</li>
        <li>• <strong className="text-text-primary">Linux</strong>: Ubuntu 20.04+, Debian 11+, or equivalent (X11/Wayland)</li>
        <li>• <strong className="text-text-primary">RAM</strong>: 4 GB minimum, 8 GB recommended</li>
        <li>• <strong className="text-text-primary">Storage</strong>: ~100 MB free space</li>
      </ul>

      <h2 id="windows" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Windows</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Download the latest <code className="px-1.5 py-0.5 rounded bg-bg-card text-xs font-mono text-indigo">.exe</code> installer from the GitHub releases page:
      </p>
      <CodeBlock
        code="# Download from GitHub releases\nhttps://github.com/Anasabubakar/glance/releases/latest"
        language="bash"
      />
      <p className="text-text-muted leading-relaxed mb-4">
        Run the installer and follow the prompts. Glance will start automatically after installation.
      </p>

      <h2 id="linux" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Linux</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Download the <code className="px-1.5 py-0.5 rounded bg-bg-card text-xs font-mono text-indigo">.deb</code> package:
      </p>
      <CodeBlock
        code={`# Download the .deb package\nwget https://github.com/Anasabubakar/glance/releases/latest/download/glance.deb\n\n# Install\nsudo dpkg -i glance.deb\n\n# Start Glance\nglance`}
        language="bash"
        filename="terminal"
      />

      <Callout type="tip" title="Build from source">
        You can also build Glance from source. See the <a href="/docs/contributing" className="text-indigo hover:underline">Contributing</a> guide for instructions.
      </Callout>
    </>
  );
}

function QuickStartContent() {
  return (
    <>
      <h2 id="step-1" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Step 1: Install Glance</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        If you haven&apos;t already, <a href="/docs/installation" className="text-indigo hover:underline">install Glance</a> on
        your system.
      </p>

      <h2 id="step-2" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Step 2: Launch</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance starts automatically on Windows after installation. On Linux, run:
      </p>
      <CodeBlock code="glance" language="bash" />

      <h2 id="step-3" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Step 3: Summon</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Press <kbd className="px-2 py-0.5 rounded bg-bg-card text-xs font-mono text-text-primary border border-border-subtle">Ctrl + Alt + M</kbd> to
        summon Glance. A small cursor buddy will appear on your screen.
      </p>

      <h2 id="step-4" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Step 4: Speak</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Talk to Glance naturally. Try saying:
      </p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>&quot;What&apos;s on my screen?&quot;</li>
        <li>&quot;Click the blue button&quot;</li>
        <li>&quot;Open my browser settings&quot;</li>
        <li>&quot;Fill in my email address&quot;</li>
      </ul>

      <h2 id="step-5" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Step 5: Configure (Optional)</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        By default, Glance works without any LLM provider — it uses its built-in capabilities. To unlock
        full power, connect an LLM provider in <a href="/docs/configuration" className="text-indigo hover:underline">Settings</a>.
      </p>

      <Callout type="info" title="No account required">
        Glance is free and open source. You can use it without creating an account or providing any API keys.
        API keys are only needed if you want to connect a cloud LLM provider.
      </Callout>
    </>
  );
}
