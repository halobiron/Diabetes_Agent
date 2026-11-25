import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import { unified } from "unified";

import type { Citation, PredictionResult } from "../types/healthcare";

export type EvidenceItem = { n: number; citation: Citation };

const parser = unified().use(remarkParse).use(remarkGfm);
const SENTENCE_SPLIT = /(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])/;

/** Keep Markdown blocks intact; list entries remain separate checklist actions. */
function actionItems(text: string): string[] {
  const root = parser.parse(text);
  const slice = (node: { position?: { start: { offset?: number }; end: { offset?: number } } }) =>
    text.slice(node.position?.start.offset, node.position?.end.offset).trim();
  const actions: string[] = [];
  let heading = "";
  for (const node of root.children) {
    if (node.type === "heading") {
      heading += `${slice(node)}\n\n`;
      continue;
    }
    if (node.type === "thematicBreak") continue;
    const blocks = node.type === "list"
      ? node.children.map((item) => {
        const content = item.children.map(slice).join("\n\n");
        // The UI supplies its own checkbox; GFM may include an unchecked marker in positions.
        return item.checked == null ? content : content.replace(/^\[[ xX]\]\s+/, "");
      })
      : node.type === "paragraph" && node.children.every((child) => child.type === "text")
        ? slice(node).split(SENTENCE_SPLIT)
        : [slice(node)];
    for (const block of blocks.filter(Boolean)) {
      actions.push(heading + block);
      heading = "";
    }
  }
  if (heading.trim()) actions.push(heading.trim());
  return actions;
}

/** Legacy fallback prose has fixed sections; LLM prose is free-form Markdown. */
export function assessmentContent(result: Pick<PredictionResult, "recommendation" | "retrieved_context">) {
  const text = result.recommendation;
  const sources = /(?:^|\n)[ \t]*(?:#{1,6}[ \t]+)?(?:\*\*|__)?Nguồn(?: tham khảo)?\s*:(?:\*\*|__)?/i.exec(text);
  const sourceText = sources ? text.slice(sources.index + sources[0].length) : "";
  const bodyWithHistory = sources ? text.slice(0, sources.index) : text;
  const history = /\s*(?:#{1,6}[ \t]+)?(?:\*\*|__)?Lịch sử đánh giá\s*:(?:\*\*|__)?/i.exec(bodyWithHistory);
  const body = history ? bodyWithHistory.slice(0, history.index) : bodyWithHistory;
  const label = /\s*(?:#{1,6}[ \t]+)?(?:\*\*|__)?Bằng chứng hướng dẫn\s*:(?:\*\*|__)?/i.exec(body);
  const before = label ? body.slice(0, label.index) : body;
  const after = label ? body.slice(label.index + label[0].length) : "";

  const sourceMap = new Map<number, { title: string; url?: string }>();
  for (const line of sourceText.split(/\n+/)) {
    const match = /^\s*\[(\d+)\]\s*(.*?)(?:\s+-\s+(https?:\/\/\S+))?\s*$/.exec(line);
    if (match) sourceMap.set(Number(match[1]), { title: match[2], url: match[3] });
  }
  const legacy: EvidenceItem[] = [];
  let end = 0;
  for (const match of after.matchAll(/([\s\S]+?)\s*\[(\d+)\]/g)) {
    const n = Number(match[2]);
    const source = sourceMap.get(n);
    legacy.push({ n, citation: {
      evidence_id: `legacy-${n}`,
      text: match[1].trim(),
      source_title: source?.title ?? "",
      url: source?.url,
    } });
    end = (match.index ?? 0) + match[0].length;
  }

  // Citation numbers follow the API order, matching the recommender's [n] markers.
  const evidence: EvidenceItem[] = result.retrieved_context.length
    ? result.retrieved_context.map((citation, index) => ({ n: index + 1, citation }))
    : legacy;
  return { actions: actionItems(before.trim()), evidence, note: after.slice(end).trim() };
}
