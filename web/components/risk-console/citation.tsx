import { ExternalLink } from "lucide-react";

import type { Citation } from "@/types/healthcare";

export function CitationLink({ citation }: { citation: Citation }) {
  const line = [citation.source_title, citation.publisher, citation.year].filter(Boolean).join(", ");
  return citation.url ? (
    <a href={citation.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-info underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-info">
      {line}<ExternalLink aria-hidden="true" className="h-3 w-3" /><span className="sr-only"> (mở trang nguồn)</span>
    </a>
  ) : (
    <span>{line}</span>
  );
}
