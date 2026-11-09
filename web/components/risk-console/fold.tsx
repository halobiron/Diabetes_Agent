import { ChevronDown } from "lucide-react";
import type { ReactNode } from "react";

import { Avatar, CAST, type CastId } from "./agents";

/** Khối phụ gập được: nhân vật phụ trách, tiêu đề, một dòng gợi ý. */
export function Fold({
  title,
  hint,
  cast,
  defaultOpen = false,
  children,
}: {
  title: string;
  hint: string;
  cast: CastId;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details open={defaultOpen} className="group rounded-2xl border-2 border-borderSoft bg-panel">
      <summary className="flex cursor-pointer list-none items-center gap-4 p-4 md:px-6 [&::-webkit-details-marker]:hidden">
        <Avatar id={cast} size={44} />
        <span className="min-w-0 flex-1">
          <span className="block text-lg font-bold" style={{ color: CAST[cast].ink }}>{title}</span>
          <span className="block text-sm text-muted">{hint}</span>
        </span>
        <ChevronDown aria-hidden="true" className="h-5 w-5 shrink-0 text-muted transition group-open:rotate-180" />
      </summary>
      <div className="p-4 pt-0 md:px-6 md:pb-6">{children}</div>
    </details>
  );
}
