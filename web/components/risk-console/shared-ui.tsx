import type { ReactNode } from "react";

export function PanelHeading({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 text-xl font-bold">
      <span className="text-info">{icon}</span>
      {title}
    </div>
  );
}
