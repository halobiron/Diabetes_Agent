"use client";

import clsx from "clsx";
import { useEffect, useState, type ReactNode } from "react";

import { Avatar, CAST, Say, useInView, type CastId, type Mood } from "./agents";

export type ActMeta = { id: CastId; title: string };

/** Một màn trình diễn: nhân vật bước ra, nói lời dẫn (gõ từng chữ), rồi phần nội dung của họ hiện ra. */
export function Act({
  id,
  title,
  line,
  mood = "neutral",
  children,
}: {
  id: CastId;
  title: string;
  line: string;
  mood?: Mood;
  children: ReactNode;
}) {
  const [ref, seen] = useInView<HTMLElement>();
  return (
    <section ref={ref} id={`act-${id}`} aria-labelledby={`act-${id}-title`} className={clsx("act scroll-mt-24", seen && "act-in")}>
      <h2 id={`act-${id}-title`} className="sr-only">{title}</h2>
      <Say id={id} text={line} mood={mood} size={88} run={seen} />
      <div className="mt-5 space-y-5 md:pl-[100px]">{children}</div>
    </section>
  );
}

/** Thanh đội hình dính trên cùng: nhân vật của màn đang xem sáng lên, bấm để nhảy tới màn đó. */
export function CastRail({ acts }: { acts: ActMeta[] }) {
  const [active, setActive] = useState<CastId | null>(acts[0]?.id ?? null);

  const key = acts.map((a) => a.id).join(",");
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id.replace("act-", "") as CastId);
      },
      { rootMargin: "-30% 0px -50% 0px", threshold: [0, 0.1, 0.5] },
    );
    for (const id of key.split(",")) {
      const node = document.getElementById(`act-${id}`);
      if (node) observer.observe(node);
    }
    return () => observer.disconnect();
  }, [key]);

  function jump(id: CastId) {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.getElementById(`act-${id}`)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }

  return (
    <nav aria-label="Các nhân vật trong đội" className="sticky top-0 z-10 -mx-5 border-b border-borderSoft bg-canvas px-5 py-2">
      <ul className="flex items-center gap-1 overflow-x-auto">
        {acts.map((act) => {
          const on = active === act.id;
          return (
            <li key={act.id}>
              <button
                type="button"
                aria-current={on ? "true" : undefined}
                onClick={() => jump(act.id)}
                className={clsx(
                  "choice flex min-h-11 items-center gap-2 rounded-full border-2 py-1 pl-1 pr-4 text-sm font-bold",
                  on ? "bg-panel" : "border-transparent text-muted hover:bg-panel",
                )}
                style={on ? { borderColor: CAST[act.id].ink, color: CAST[act.id].ink } : undefined}
              >
                <Avatar id={act.id} size={on ? 34 : 28} mood={on ? "happy" : "neutral"} />
                <span className="whitespace-nowrap">{CAST[act.id].name}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
