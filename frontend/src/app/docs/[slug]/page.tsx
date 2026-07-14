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
