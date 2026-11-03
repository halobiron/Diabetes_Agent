import clsx from "clsx";

import type { TabKey } from "./types";

export function Tabs({ activeTab, onChange }: { activeTab: TabKey; onChange: (tab: TabKey) => void }) {
  const tabs: Array<{ key: TabKey; label: string }> = [
    { key: "assessment", label: "Đánh giá" },
    { key: "evidence", label: "Bằng chứng" },
    { key: "history", label: "Lịch sử" },
  ];

  return (
    <div className="flex flex-wrap gap-2 border-b border-borderSoft pb-3">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          onClick={() => onChange(tab.key)}
          className={clsx(
            "rounded-md px-4 py-2 text-sm font-semibold transition",
            activeTab === tab.key
              ? "bg-info text-canvas"
              : "border border-borderSoft bg-panel text-muted hover:text-ink",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
