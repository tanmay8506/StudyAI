import { PipelineProgressView } from '@/components/pipeline/PipelineProgressView';

export default async function PipelinePage({ params }: { params: { upc: string } }) {
  // Await params as required by Next.js 15+ if needed, but simple destructuring usually works.
  const { upc } = await params;

  return (
    <main className="min-h-screen bg-background">
      <PipelineProgressView upc={upc} />
    </main>
  );
}
