"use client";

import clsx from "clsx";
import { useEffect, useRef, useState, type ReactNode } from "react";

export type CastId = "tiep" | "mo" | "nho" | "chung" | "luat" | "goi";
export type Mood = "neutral" | "happy" | "worried" | "think" | "talk" | "wave";

export type CastMember = {
  id: CastId;
  name: string;
  role: string;
  /** Màu mực con dấu của nhân vật, đủ tương phản trên nền trắng. */
  ink: string;
  /** Nền nhạt của avatar. */
  tint: string;
};

export const CAST: Record<CastId, CastMember> = {
  tiep: { id: "tiep", name: "Bé Tiếp", role: "Tiếp đón, hỏi hồ sơ", ink: "#a8530d", tint: "#ffe3bd" },
  mo: { id: "mo", name: "Ông Mô", role: "Mô hình dự đoán, giải thích", ink: "#4b3fa8", tint: "#dcd7f7" },
  nho: { id: "nho", name: "Bà Nhớ", role: "Bộ nhớ hồ sơ tương tự", ink: "#8a2f6b", tint: "#f6d8ea" },
  chung: { id: "chung", name: "Cô Chứng", role: "Truy xuất bằng chứng", ink: "#1b6b4d", tint: "#cdeedd" },
  luat: { id: "luat", name: "Chú Luật", role: "Luật an toàn", ink: "#b3261e", tint: "#ffd5d0" },
  goi: { id: "goi", name: "Bạn Gợi", role: "Khuyến nghị, what-if", ink: "#0b6b86", tint: "#cdebf4" },
};

/** Mỗi thành phần phía API do nhân vật nào phụ trách. */
export const COMPONENT_CAST: Record<string, { cast: CastId; label: string }> = {
  risk_model: { cast: "mo", label: "Mô hình dự đoán" },
  feature_explainer: { cast: "mo", label: "Giải thích đặc trưng" },
  explainer: { cast: "mo", label: "Giải thích bằng lời" },
  memory_search: { cast: "nho", label: "Tìm hồ sơ tương tự" },
  memory_store: { cast: "nho", label: "Lưu hồ sơ vào bộ nhớ" },
  retriever: { cast: "chung", label: "Truy xuất bằng chứng (KB + RAG)" },
  safety_guard: { cast: "luat", label: "Kiểm tra luật an toàn" },
  recommender: { cast: "goi", label: "Soạn khuyến nghị" },
  support_policy: { cast: "goi", label: "Policy học tăng cường" },
  what_if: { cast: "goi", label: "Mô phỏng nếu thay đổi" },
};

const SKIN = "#f6c9a6";
const LINE = "#2a2547";
const BLINK_DELAY: Record<CastId, string> = { tiep: "0s", mo: "1.3s", nho: "2.1s", chung: "0.6s", luat: "1.8s", goi: "2.7s" };

/** Avatar SVG có biểu cảm: chớp mắt, thở, nói, vẫy tay, lo lắng, suy nghĩ. */
export function Avatar({
  id,
  size = 48,
  mood = "neutral",
  working = false,
  className,
}: {
  id: CastId;
  size?: number;
  mood?: Mood;
  working?: boolean;
  className?: string;
}) {
  const m = CAST[id];
  const happy = mood === "happy";
  const worried = mood === "worried";
  const think = mood === "think";
  const talk = mood === "talk";
  const wave = mood === "wave";

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      aria-hidden="true"
      className={clsx("avatar shrink-0 overflow-visible", working && "avatar-working", happy && "avatar-hop", className)}
    >
      <circle cx="32" cy="32" r="32" fill={m.tint} />
      <g className="av-breathe">
        <path d="M10 64c2-13 11-18 22-18s20 5 22 18z" fill={m.ink} />
        <rect x="28" y="40" width="8" height="8" rx="3" fill={SKIN} />
        {wave ? (
          <g className="av-arm">
            <path d="M47 56c5-4 7-9 7-15" stroke={m.ink} strokeWidth="6" strokeLinecap="round" fill="none" />
            <circle cx="54" cy="37" r="4.2" fill={SKIN} />
          </g>
        ) : null}
        <g className={clsx(think && "av-tilt")}>
          <ellipse cx="32" cy="30" rx="13" ry="14" fill={SKIN} />
          {id === "tiep" ? (
            <>
              <path d="M18 24c2-10 26-10 28 0-6-4-22-4-28 0z" fill="#fff" stroke={LINE} strokeWidth="1.5" />
              <path d="M32 14v6M29 17h6" stroke={m.ink} strokeWidth="2" strokeLinecap="round" />
            </>
          ) : null}
          {id === "mo" ? (
            <>
              <path d="M18 27c0-12 28-12 28 0-3-6-25-6-28 0z" fill="#b9b6cf" />
              <circle cx="26" cy="31" r="4.5" fill="none" stroke={LINE} strokeWidth="1.6" />
              <circle cx="38" cy="31" r="4.5" fill="none" stroke={LINE} strokeWidth="1.6" />
              <path d="M30.5 31h3" stroke={LINE} strokeWidth="1.6" />
            </>
          ) : null}
          {id === "nho" ? (
            <>
              <path d="M18 28c-1-13 27-13 28 0-4-7-24-7-28 0z" fill="#6a5b73" />
              <circle cx="32" cy="14" r="5" fill="#6a5b73" />
            </>
          ) : null}
          {id === "chung" ? (
            <>
              <path d="M18 32c-3-17 25-20 28 0-1-8-4-11-14-11s-13 3-14 11z" fill="#3b2f2a" />
              <path d="M19 24c8-5 18-5 26 0" fill="none" stroke={m.ink} strokeWidth="3" strokeLinecap="round" />
            </>
          ) : null}
          {id === "luat" ? (
            <>
              <path d="M17 26c1-12 29-12 30 0z" fill={m.ink} />
              <rect x="14" y="25" width="36" height="4" rx="2" fill="#7a1a15" />
              <path d="M32 11l4 2v4c0 2-2 3-4 4-2-1-4-2-4-4v-4z" fill="#ffd25e" />
            </>
          ) : null}
          {id === "goi" ? <path d="M19 26l2-10 6 6 5-9 5 9 6-6 2 10c-6-4-20-4-26 0z" fill="#27455a" /> : null}

          {/* lông mày theo cảm xúc */}
          <g stroke={LINE} strokeWidth="1.6" strokeLinecap="round" fill="none">
            {worried ? (
              <>
                <path d="M22.5 29l6-2" />
                <path d="M35.5 27l6 2" />
              </>
            ) : happy ? (
              <>
                <path d="M22.5 27.5q3-2.5 6 0" />
                <path d="M35.5 27.5q3-2.5 6 0" />
              </>
            ) : null}
          </g>

          <g className="av-eyes" style={{ animationDelay: BLINK_DELAY[id] }} fill={LINE}>
            {happy ? (
              <>
                <path d="M23.5 33q3-4 6 0" stroke={LINE} strokeWidth="1.8" fill="none" strokeLinecap="round" />
                <path d="M34.5 33q3-4 6 0" stroke={LINE} strokeWidth="1.8" fill="none" strokeLinecap="round" />
              </>
            ) : (
              <>
                <circle cx="26.5" cy="32" r="1.9" />
                <circle cx="37.5" cy="32" r="1.9" />
              </>
            )}
          </g>

          {/* miệng */}
          {happy ? (
            <path d="M25.5 37h13c0 5-3 8-6.5 8s-6.5-3-6.5-8z" fill="#7a2a2a" />
          ) : worried ? (
            <path d="M27 42c3-3 7-3 10 0" fill="none" stroke={LINE} strokeWidth="1.8" strokeLinecap="round" />
          ) : think ? (
            <circle cx="35" cy="40" r="1.9" fill={LINE} />
          ) : talk ? (
            <ellipse className="av-mouth" cx="32" cy="40" rx="3.6" ry="3" fill="#7a2a2a" />
          ) : (
            <path d="M27 38c3 3 7 3 10 0" fill="none" stroke={LINE} strokeWidth="1.8" strokeLinecap="round" />
          )}
        </g>
      </g>
      {worried ? <path className="av-sweat" d="M47 18c2.5 3.5 3.5 5.5 3.5 7a3.5 3.5 0 0 1-7 0c0-1.500 1-3.500 3.500-7z" fill="#7cc4e8" /> : null}
      {think ? (
        <g fill="#fff" stroke={m.ink} strokeWidth="1.2" className="av-think">
          <circle cx="50" cy="20" r="1.8" />
          <circle cx="54" cy="13" r="2.6" />
          <circle cx="59" cy="5" r="3.6" />
        </g>
      ) : null}
    </svg>
  );
}

/** Quan sát phần tử đã vào khung nhìn chưa (chỉ kích hoạt một lần). */
export function useInView<T extends Element>(): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node || seen) return;
    if (typeof IntersectionObserver === "undefined") {
      setSeen(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [seen]);
  return [ref, seen];
}

/** Gõ chữ từng ký tự; tôn trọng prefers-reduced-motion. */
export function useTypewriter(text: string, run = true, charsPerSecond = 55): { shown: string; done: boolean } {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!run) {
      setCount(0);
      return;
    }
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setCount(text.length);
      return;
    }
    setCount(0);
    const timer = window.setInterval(() => {
      setCount((value) => {
        if (value >= text.length) {
          window.clearInterval(timer);
          return value;
        }
        return value + 1;
      });
    }, 1000 / charsPerSecond);
    return () => window.clearInterval(timer);
  }, [text, run, charsPerSecond]);
  return { shown: text.slice(0, count), done: count >= text.length };
}

/** Nhân vật nói: avatar + bóng thoại. Có `text` thì gõ chữ và nhép miệng khi đang nói. */
export function Say({
  id,
  text,
  children,
  mood = "neutral",
  size = 56,
  run = true,
  className,
}: {
  id: CastId;
  text?: string;
  children?: ReactNode;
  mood?: Mood;
  size?: number;
  run?: boolean;
  className?: string;
}) {
  const m = CAST[id];
  const typed = useTypewriter(text ?? "", run && text !== undefined);
  const speaking = text !== undefined && run && !typed.done;

  return (
    <div className={clsx("flex items-end gap-3", className)}>
      <Avatar id={id} size={size} mood={speaking ? "talk" : mood} />
      <div className="min-w-0 max-w-prose">
        <div className="mb-1 text-sm font-semibold" style={{ color: m.ink }}>{m.name}</div>
        <div className="bubble rounded-2xl rounded-bl-sm border-2 bg-panel px-4 py-3 text-base leading-7 text-ink" style={{ borderColor: `${m.ink}55` }}>
          {text !== undefined ? (
            <>
              <span className="sr-only">{text}</span>
              <span aria-hidden="true">
                {typed.shown}
                {speaking ? <span className="caret" /> : null}
              </span>
            </>
          ) : (
            children
          )}
        </div>
      </div>
    </div>
  );
}

/** Bóng thoại không kèm avatar, dùng khi nhân vật nói nhiều câu liên tiếp. */
export function Bubble({ id, children, className }: { id: CastId; children: ReactNode; className?: string }) {
  return (
    <div
      className={clsx("bubble rounded-2xl border-2 bg-panel px-4 py-3 text-base leading-7 text-ink [overflow-wrap:anywhere]", className)}
      style={{ borderColor: `${CAST[id].ink}55` }}
    >
      {children}
    </div>
  );
}

/** Con dấu mực của nhân vật; nghiêng nhẹ như đóng bằng tay. */
export function Seal({ id, children, tilt = -4, className }: { id: CastId; children: ReactNode; tilt?: number; className?: string }) {
  const m = CAST[id];
  return (
    <span
      className={clsx("inline-block rounded-lg border-[3px] border-double px-3 py-1 text-sm font-bold uppercase tracking-wide", className)}
      style={{ color: m.ink, borderColor: m.ink, transform: `rotate(${tilt}deg)` }}
    >
      {children}
    </span>
  );
}
