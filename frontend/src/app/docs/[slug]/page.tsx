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

function FeaturesContent() {
  return (
    <>
      <h2 id="screen-vision" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Screen Vision</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance captures and understands your screen in real-time. It can read text, identify UI elements,
        recognize images, and understand the context of what you&apos;re working on.
      </p>

      <h2 id="cursor-buddy" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Cursor Buddy</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Unlike chat-based assistants, Glance appears as a small companion near your cursor. It visually
        points at exactly what it&apos;s referring to, eliminating any ambiguity.
      </p>

      <h2 id="action-execution" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Action Execution</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance can take real actions on your desktop:
      </p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Click buttons and links</li>
        <li>• Type text into fields</li>
        <li>• Scroll through pages</li>
        <li>• Navigate between windows</li>
        <li>• Fill out forms</li>
        <li>• Copy and paste content</li>
      </ul>

      <h2 id="voice-first" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Voice-First Interface</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance is designed for voice interaction. Speak naturally and it understands context, pronouns
        (&quot;click that&quot;, &quot;scroll down there&quot;), and multi-step instructions.
      </p>

      <h2 id="memory" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Memory & Learning</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance remembers your preferences, workflows, and past interactions. Over time, it becomes
        increasingly tailored to how you work.
      </p>

      <h2 id="privacy" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Privacy</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        All screen processing happens locally on your device. When using cloud LLMs, only the relevant
        context is sent — never raw screen recordings. With Ollama, everything stays fully offline.
      </p>
    </>
  );
}

function ArchitectureContent() {
  return (
    <>
      <h2 id="overview" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Overview</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance is built as a cross-platform desktop application with a modular architecture. Its components work together to capture context, coordinate model providers, and execute actions locally.
      </p>

      <h2 id="components" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Core Components</h2>
      <ul className="space-y-3 text-text-muted mb-6">
        <li className="flex gap-2">
          <span className="text-indigo font-bold">1.</span>
          <span><strong className="text-text-primary">Screen Capture</strong> — Captures screen content using native APIs</span>
        </li>
        <li className="flex gap-2">
          <span className="text-indigo font-bold">2.</span>
          <span><strong className="text-text-primary">Vision Pipeline</strong> — Processes screenshots to extract text and UI elements</span>
        </li>
        <li className="flex gap-2">
          <span className="text-indigo font-bold">3.</span>
          <span><strong className="text-text-primary">LLM Router</strong> — Routes requests to the configured LLM provider</span>
        </li>
        <li className="flex gap-2">
          <span className="text-indigo font-bold">4.</span>
          <span><strong className="text-text-primary">Action Engine</strong> — Executes clicks, typing, scrolling via OS-level APIs</span>
        </li>
        <li className="flex gap-2">
          <span className="text-indigo font-bold">5.</span>
          <span><strong className="text-text-primary">Cursor Buddy</strong> — The overlay UI that follows your cursor</span>
        </li>
      </ul>

      <h2 id="tech-stack" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Tech Stack</h2>
      <CodeBlock
        code={`Framework:    Electron\nFrontend:     React + TypeScript\nBackend:      Node.js\nScreen Cap:   Native OS APIs\nVoice:        Web Speech API / Whisper\nBuild:        electron-builder`}
        language="yaml"
        filename="tech-stack"
      />
    </>
  );
}

function ConfigurationContent() {
  return (
    <>
      <h2 id="settings-file" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Settings File</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance stores its configuration in a JSON file:
      </p>
      <CodeBlock
        code={`# Windows\n%APPDATA%/Glance/config.json\n\n# Linux\n~/.config/glance/config.json`}
        language="bash"
        filename="config location"
      />

      <h2 id="llm-provider" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">LLM Provider</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Set your preferred LLM provider. Glance works without one, but connecting a provider
        unlocks full capabilities.
      </p>
      <CodeBlock
        code={`{\n  "provider": "claude",\n  "apiKey": "sk-ant-...",\n  "model": "claude-sonnet-4-20250514"\n}`}
        language="json"
        filename="config.json"
      />

      <h2 id="hotkey" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Custom Hotkey</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Change the summon hotkey from the default <kbd className="px-1.5 py-0.5 rounded bg-bg-card text-xs font-mono border border-border-subtle">Ctrl + Alt + M</kbd>:
      </p>
      <CodeBlock
        code={`{\n  "hotkey": "ctrl+shift+space"\n}`}
        language="json"
        filename="config.json"
      />

      <h2 id="voice" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Voice Settings</h2>
      <CodeBlock
        code={`{\n  "voice": {\n    "enabled": true,\n    "engine": "whisper",\n    "language": "en",\n    "autoListen": true\n  }\n}`}
        language="json"
        filename="config.json"
      />

      <Callout type="tip" title="Hot reload">
        Changes to the config file are picked up automatically — no restart needed.
      </Callout>
    </>
  );
}

function VoiceCommandsContent() {
  return (
    <>
      <h2 id="basics" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Basic Commands</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance understands natural language. You don&apos;t need to memorize specific phrases — just
        speak naturally.
      </p>
      <div className="rounded-xl border border-border-subtle overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle bg-bg-card/30">
              <th className="text-left px-4 py-3 font-medium text-text-primary">Command</th>
              <th className="text-left px-4 py-3 font-medium text-text-primary">What it does</th>
            </tr>
          </thead>
          <tbody className="text-text-muted">
            <tr className="border-b border-border-subtle"><td className="px-4 py-2.5">&quot;What&apos;s on my screen?&quot;</td><td className="px-4 py-2.5">Describes the current screen</td></tr>
            <tr className="border-b border-border-subtle"><td className="px-4 py-2.5">&quot;Click the submit button&quot;</td><td className="px-4 py-2.5">Finds and clicks the button</td></tr>
            <tr className="border-b border-border-subtle"><td className="px-4 py-2.5">&quot;Type my email&quot;</td><td className="px-4 py-2.5">Types your saved email</td></tr>
            <tr className="border-b border-border-subtle"><td className="px-4 py-2.5">&quot;Scroll down&quot;</td><td className="px-4 py-2.5">Scrolls the active window</td></tr>
            <tr><td className="px-4 py-2.5">&quot;Go back&quot;</td><td className="px-4 py-2.5">Navigates to the previous page</td></tr>
          </tbody>
        </table>
      </div>

      <h2 id="contextual" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Contextual Commands</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance understands context and pronouns:
      </p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• &quot;Click <strong className="text-text-primary">that</strong>&quot; — clicks the element Glance is pointing at</li>
        <li>• &quot;Read <strong className="text-text-primary">this</strong>&quot; — reads the content under focus</li>
        <li>• &quot;Move <strong className="text-text-primary">there</strong>&quot; — moves to where you gesture</li>
      </ul>
    </>
  );
}

function LLMProvidersContent() {
  return (
    <>
      <h2 id="supported" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Supported Providers</h2>

      {[
        { name: "Claude (Anthropic)", dot: "#D4A574", config: `"provider": "claude",\n"apiKey": "sk-ant-..."` },
        { name: "OpenAI", dot: "#10A37F", config: `"provider": "openai",\n"apiKey": "sk-..."` },
        { name: "Google Gemini", dot: "#4285F4", config: `"provider": "gemini",\n"apiKey": "AI..."` },
        { name: "Ollama (Local)", dot: "#FFFFFF", config: `"provider": "ollama",\n"baseUrl": "http://localhost:11434"` },
        { name: "Glance Cloud (free, default)", dot: "#34D399", config: `"provider": "cloud"` },
        { name: "Custom endpoint (BYOK)", dot: "#A78BFA", config: `"provider": "custom",\n"baseUrl": "https://openrouter.ai/api/v1",\n"apiKey": "sk-...",\n"model": "anthropic/claude-sonnet-4.5"` },
      ].map((p) => (
        <div key={p.name} className="mb-8">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.dot }} />
            {p.name}
          </h3>
          <CodeBlock code={`{\n  ${p.config}\n}`} language="json" filename="config.json" />
        </div>
      ))}

      <Callout type="info" title="Free by default">
        With no key set, Glance uses Glance Cloud, a free hosted text model. It is text-only
        (screenshots are not uploaded) and rate-limited. For screen-aware features use Ollama
        or a vision model on your own endpoint. Set GLANCE_NO_CLOUD=1 to opt out.
      </Callout>

      <Callout type="info" title="No provider needed">
        Glance works without any LLM provider for basic screen reading and pointing. Providers
        unlock advanced reasoning and action capabilities.
      </Callout>
    </>
  );
}

function KeyboardShortcutsContent() {
  return (
    <>
      <h2 id="global" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Global Shortcuts</h2>
      <div className="rounded-xl border border-border-subtle overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle bg-bg-card/30">
              <th className="text-left px-4 py-3 font-medium text-text-primary">Shortcut</th>
              <th className="text-left px-4 py-3 font-medium text-text-primary">Action</th>
            </tr>
          </thead>
          <tbody className="text-text-muted">
            <tr className="border-b border-border-subtle"><td className="px-4 py-2.5"><kbd className="px-1.5 py-0.5 rounded bg-bg-card text-xs font-mono border border-border-subtle">Ctrl+Alt+M</kbd></td><td className="px-4 py-2.5">Summon/dismiss Glance</td></tr>
            <tr className="border-b border-border-subtle"><td className="px-4 py-2.5"><kbd className="px-1.5 py-0.5 rounded bg-bg-card text-xs font-mono border border-border-subtle">Ctrl+Alt+V</kbd></td><td className="px-4 py-2.5">Toggle voice input</td></tr>
            <tr className="border-b border-border-subtle"><td className="px-4 py-2.5"><kbd className="px-1.5 py-0.5 rounded bg-bg-card text-xs font-mono border border-border-subtle">Ctrl+Alt+S</kbd></td><td className="px-4 py-2.5">Take screenshot for context</td></tr>
            <tr><td className="px-4 py-2.5"><kbd className="px-1.5 py-0.5 rounded bg-bg-card text-xs font-mono border border-border-subtle">Esc</kbd></td><td className="px-4 py-2.5">Dismiss Glance</td></tr>
          </tbody>
        </table>
      </div>
    </>
  );
}

function FAQContent() {
  return (
    <>
      {[
        { q: "Is Glance free?", a: "Yes. Glance is free and open source under the MIT license." },
        { q: "Does Glance record my screen?", a: "No. Screen captures are processed locally and never stored permanently. When using cloud LLMs, only extracted text/context is sent — never raw screenshots." },
        { q: "Can I use Glance offline?", a: "Yes. Use Ollama as your LLM provider for fully local, offline operation. Basic screen reading works without any provider." },
        { q: "Does Glance work on macOS?", a: "Not yet. Glance currently supports Windows and Linux. macOS support is on the roadmap." },
        { q: "Is my data safe?", a: "Yes. Glance is open source — you can audit every line of code. Screen data stays local. Memory is stored only on your device." },
      ].map((item) => (
        <div key={item.q} className="mb-8">
          <h3 className="text-lg font-semibold mb-2">{item.q}</h3>
          <p className="text-text-muted leading-relaxed">{item.a}</p>
        </div>
      ))}
    </>
  );
}

function TroubleshootingContent() {
  return (
    <>
      <h2 id="common" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Common Issues</h2>

      <h3 className="text-lg font-semibold mt-8 mb-3">Glance doesn&apos;t appear when I press the hotkey</h3>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Make sure Glance is running in the system tray</li>
        <li>• Check that no other app is using the same hotkey</li>
        <li>• Try running Glance as administrator (Windows)</li>
      </ul>

      <h3 className="text-lg font-semibold mt-8 mb-3">Voice input isn&apos;t working</h3>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Check microphone permissions in your OS settings</li>
        <li>• Make sure voice is enabled in Glance settings</li>
        <li>• Try selecting a different microphone device</li>
      </ul>

      <h3 className="text-lg font-semibold mt-8 mb-3">Screen capture is blank</h3>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• On Linux, ensure screen capture permissions are granted</li>
        <li>• Wayland users may need to grant additional permissions</li>
        <li>• Try restarting Glance</li>
      </ul>

      <Callout type="warning" title="Still stuck?">
        Open an issue on <a href="https://github.com/Anasabubakar/glance/issues" target="_blank" rel="noopener noreferrer" className="text-indigo hover:underline">GitHub</a> with
        your OS version and Glance version.
      </Callout>
    </>
  );
}

function ChangelogContent() {
  return (
    <>
      <h2 id="v0-3-19" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.19 — Automations</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Fast, exact automations handle most everyday requests with no AI: windows, apps, system settings, shortcuts, files, local answers and web helpers</li>
        <li>• Chains of commands run every part or none of it</li>
        <li>• Your own routines, timers, reminders and schedules, managed on the new Automations page</li>
        <li>• Macros, and a fix so the first click or stroke is never lost</li>
      </ul>

      <h2 id="v0-3-18" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.18 — Typing, drag and drop, drawing</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Typing fixed: the first text typed no longer gets lost</li>
        <li>• Drag and drop, selecting and resizing</li>
        <li>• Draw shapes or freehand with the mouse, and annotate the screen (circle, underline, arrow, label)</li>
        <li>• Triple-click, middle-click, hover and ctrl/shift/alt-click</li>
      </ul>

      <h2 id="v0-3-17" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.17 — Instant, verified, safer</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Everyday commands (windows, apps, volume, keys, time, search) run instantly with no AI</li>
        <li>• Glance verifies that an action changed the screen; Esc stops it; it asks before risky steps</li>
        <li>• Click accuracy is measured per model and the best one is preferred</li>
        <li>• One-click checkup on the Diagnostics page; Lesson Recording and Workflow Capture work on GNOME Wayland</li>
        <li>• API keys are masked in the console, logs and diagnostics</li>
      </ul>

      <h2 id="v0-3-16" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.16 — Open any app</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Opens any installed app by name, including Text Editor for &quot;notepad&quot;</li>
        <li>• Gemini gives up after 45 seconds and hands over to your next provider</li>
        <li>• Glance says so out loud when every provider is busy</li>
      </ul>

      <h2 id="v0-3-15" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.15 — Provider priority</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Choose every provider you want and set their priority; Glance falls back down the list</li>
        <li>• Several keys for Gemini, Claude, OpenAI, Groq and OpenRouter, spread automatically</li>
        <li>• The Glance icon now shows in the dock on Wayland</li>
      </ul>

      <h2 id="v0-3-14" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.14 — Many keys, more providers</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Add several Gemini keys; requests are spread across them and a key at its limit is skipped</li>
        <li>• Groq and OpenRouter support, with free models listed on the Models page</li>
        <li>• Automatic fallback to your other providers when the chosen one is busy or out of quota</li>
      </ul>

      <h2 id="v0-3-13" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.13 — Fast, visible actions</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• About 2-3 seconds per step with Gemini: two models are asked at once and the first good answer wins</li>
        <li>• Glance clicks the visible button so you see the cursor go there, instead of using a hidden shortcut</li>
        <li>• If Gemini is too busy, Glance says so within 40 seconds instead of retrying for minutes</li>
      </ul>

      <h2 id="v0-3-12" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.12 — Accurate clicks</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Clicks and pointing with Gemini now use its 0-1000 grid, so they land on the target</li>
        <li>• Glance never reads action names or coordinates aloud</li>
        <li>• Keyboard shortcuts are preferred, and Glance stops honestly if it is stuck</li>
      </ul>

      <h2 id="v0-3-11" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.11 — Fast answers, visible steps</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Gemini: the fastest healthy model is tried first, slow or busy ones are skipped and remembered</li>
        <li>• The cursor now flies to each target and hovers before clicking</li>
        <li>• Keys, typing and app launches show a caption beside the cursor</li>
      </ul>

      <h2 id="v0-3-10" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.10 — Screen capture and clicks fixed</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Screen capture, clicks and typing now work in the installed app on GNOME</li>
        <li>• Minimize, switch, copy, save and similar requests go straight to the action path</li>
        <li>• Glance no longer claims to see your screen when no screenshot was captured</li>
      </ul>

      <h2 id="v0-3-9" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.9 — Text and vision models</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Choose a text model and a vision model separately on the Models page</li>
        <li>• Model choices apply immediately, including provider switches</li>
        <li>• New default ElevenLabs voice</li>
      </ul>

      <h2 id="v0-3-8" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.8 — Faster answers</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Requests are sorted locally for Gemini, Ollama and custom endpoints, removing a slow extra model call</li>
        <li>• Wake-word listening pauses while Glance is working</li>
        <li>• Clear message to log out and back in when the GNOME extension is out of date</li>
      </ul>

      <h2 id="v0-3-7" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.7 — Your own key, fast models</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Glance Cloud is paused: use your own Gemini, Claude, OpenAI or OpenAI-compatible key, or local Ollama</li>
        <li>• Faster default models: Claude Haiku 4.5, GPT-4o mini, newest Gemini Flash</li>
        <li>• Qwen2.5-VL 3B is the first recommended local vision model</li>
      </ul>

      <h2 id="v0-3-6" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.6 — A redesigned app</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Completely redesigned dashboard: 9 pages instead of 17, with a new design system and icons</li>
        <li>• AI &amp; Keys: providers, keys and the custom endpoint in one place</li>
        <li>• Floating panel with clear states and a working Hold to talk button</li>
        <li>• Settings show real defaults, apply immediately and match the tray menu; secrets are always masked</li>
        <li>• Screen capture, clicks and typing on GNOME/Wayland through the extension (log out and back in once)</li>
        <li>• Gemini works again: Glance picks a model your key can actually use</li>
        <li>• The words after &quot;Glance&quot; are used as the command, and listening ends when you stop talking</li>
      </ul>

      <h2 id="v0-3-5" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.5 — Glance Cloud fixes</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Fixed Glance Cloud getting stuck on &quot;HTTP Error 429&quot;; the key is now saved and errors are clear</li>
        <li>• Free-tier replies are much faster (about 6 s to first word, then about 1 s)</li>
        <li>• Wake word ignores steady room noise and invented text</li>
      </ul>

      <h2 id="v0-3-4" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.4 — Hotkey and voice on GNOME</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• The push-to-talk hotkey now works on GNOME/Wayland (grabbed in the compositor by the extension)</li>
        <li>• More forgiving wake word, with wake-word activity logged for troubleshooting</li>
        <li>• Log out and back in once after updating so GNOME loads the updated extension</li>
      </ul>

      <h2 id="v0-3-3" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.3 — Linux launch fix</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Fixed the Linux .deb and AppImage exiting at startup with &quot;shell import failed&quot;</li>
        <li>• The release build now smoke-tests the packaged Linux app before shipping</li>
      </ul>

      <h2 id="v0-3-2" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.2 — Dashboard fix</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Fixed a startup crash that stopped the dashboard from opening in v0.3.0 and v0.3.1</li>
        <li>• The Custom endpoint (BYOK) form is reachable again</li>
      </ul>

      <h2 id="v0-3-1" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.1 — Always-on-top cursor on GNOME</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• The buddy cursor stays above every window and workspace on GNOME</li>
        <li>• Smooth pointer following drawn by a small GNOME Shell extension</li>
        <li>• No taskbar or alt-tab entry for the cursor</li>
        <li>• X11: overlay pinned to all desktops and re-raised automatically</li>
        <li>• Log out and back in once after the first launch to enable it</li>
      </ul>

      <h2 id="v0-3-0" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.3.0 — Free Glance Cloud and BYOK</h2>
      <p className="text-text-dim text-sm mb-4">October 2026</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Glance Cloud: free hosted text model, the default when no key is set</li>
        <li>• Custom (BYOK) provider for any OpenAI-compatible endpoint</li>
        <li>• Custom endpoint form on the API Keys page</li>
        <li>• Automatic retry when the shared free tier is busy</li>
      </ul>

      <h2 id="v0-1-0" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">v0.1.0 — Initial Release</h2>
      <p className="text-text-dim text-sm mb-4">July 2025</p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Initial public release</li>
        <li>• Real-time screen vision</li>
        <li>• Cursor buddy companion</li>
        <li>• Action execution (click, type, scroll)</li>
        <li>• Voice-first interface</li>
        <li>• Multi-LLM support (Claude, OpenAI, Gemini, Ollama)</li>
        <li>• Windows + Linux support</li>
        <li>• MIT License</li>
      </ul>
    </>
  );
}

function RoadmapContent() {
  return (
    <>
      <h2 id="in-progress" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">In Progress</h2>
      <ul className="space-y-2 text-text-muted mb-8">
        <li>• Multi-monitor support</li>
        <li>• Plugin system for custom actions</li>
        <li>• Improved voice recognition accuracy</li>
      </ul>

      <h2 id="planned" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Planned</h2>
      <ul className="space-y-2 text-text-muted mb-8">
        <li>• macOS support</li>
        <li>• Workflow automation (record and replay)</li>
        <li>• Browser extension</li>
        <li>• Mobile companion app</li>
      </ul>

      <h2 id="exploring" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Exploring</h2>
      <ul className="space-y-2 text-text-muted mb-8">
        <li>• AR/VR support</li>
        <li>• Team collaboration features</li>
        <li>• API for developers</li>
      </ul>
    </>
  );
}

function ContributingContent() {
  return (
    <>
      <h2 id="getting-started" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Getting Started</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Glance is open source and welcomes contributions. Here&apos;s how to get set up:
      </p>
      <CodeBlock
        code={`# Clone the repo\ngit clone https://github.com/Anasabubakar/glance.git\ncd Glance\n\n# Install dependencies\nnpm install\n\n# Start development\nnpm run dev`}
        language="bash"
        filename="terminal"
      />

      <h2 id="guidelines" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Guidelines</h2>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Follow the existing code style</li>
        <li>• Write meaningful commit messages</li>
        <li>• Add tests for new features</li>
        <li>• Update documentation when changing behavior</li>
        <li>• Be respectful in discussions</li>
      </ul>

      <h2 id="issues" className="text-xl font-semibold mt-10 mb-4 scroll-mt-20">Reporting Issues</h2>
      <p className="text-text-muted leading-relaxed mb-4">
        Found a bug? Open an issue on <a href="https://github.com/Anasabubakar/glance/issues" target="_blank" rel="noopener noreferrer" className="text-indigo hover:underline">GitHub</a> with:
      </p>
      <ul className="space-y-2 text-text-muted mb-6">
        <li>• Your OS and version</li>
        <li>• Glance version</li>
        <li>• Steps to reproduce</li>
        <li>• Expected vs actual behavior</li>
      </ul>
    </>
  );
}
