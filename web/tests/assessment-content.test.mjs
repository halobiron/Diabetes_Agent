import assert from "node:assert/strict";
import test from "node:test";

import { assessmentContent } from "../lib/assessment-content.ts";

const citations = [
  { evidence_id: "kb-1", text: "**Đoạn hướng dẫn thứ nhất.**", source_title: "Nguồn A", publisher: "A", year: 2025, url: "https://example.com/a" },
  { evidence_id: "kb-2", text: "Đoạn hướng dẫn thứ hai.", source_title: "Nguồn B" },
];

test("LLM recommendations without the fixed label still display every retrieved passage in citation order", () => {
  const result = assessmentContent({ recommendation: "## Khuyến nghị\n\n- **Theo dõi** [2].\n- Trao đổi với bác sĩ [1].", retrieved_context: citations });
  assert.deepEqual(result.evidence, citations.map((citation, index) => ({ n: index + 1, citation })));
  assert.equal(result.actions.length, 2);
  assert.match(result.actions[0], /\*\*Theo dõi\*\* \[2\]/);
});

test("structured passages take precedence over shortened fallback prose", () => {
  const result = assessmentContent({ recommendation: "Theo dõi. Bằng chứng hướng dẫn: Bản rút gọn [1]", retrieved_context: citations });
  assert.equal(result.evidence[0].citation.text, citations[0].text);
  assert.equal(result.evidence.length, 2);
  assert.deepEqual(result.actions, ["Theo dõi."]);
});

test("legacy fallback retains sources, evidence and limitations", () => {
  const result = assessmentContent({
    recommendation: "Theo dõi. Bằng chứng hướng dẫn: Đoạn một [1] Đoạn hai [2] Bằng chứng còn hạn chế.\n\nNguồn tham khảo:\n[1] Nguồn A - https://example.com/a\n[2] Nguồn B",
    retrieved_context: [],
  });
  assert.deepEqual(result.evidence.map(({ n, citation }) => [n, citation.text, citation.source_title, citation.url]), [
    [1, "Đoạn một", "Nguồn A", "https://example.com/a"],
    [2, "Đoạn hai", "Nguồn B", undefined],
  ]);
  assert.equal(result.note, "Bằng chứng còn hạn chế.");
});

test("Markdown lists and headings survive; history and source sections stay out of the checklist", () => {
  const result = assessmentContent({
    recommendation: "### Khuyến nghị\n\n1. **Theo dõi. Tiếp tục ghi nhận.** [1]\n2. Xem [nguồn](https://example.com).\n\n## **Lịch sử đánh giá:**\nSố đo lần trước.\n\n### **Nguồn tham khảo:**\n[1] Nguồn A - https://example.com/a",
    retrieved_context: citations,
  });
  assert.deepEqual(result.actions, ["### Khuyến nghị\n\n**Theo dõi. Tiếp tục ghi nhận.** [1]", "Xem [nguồn](https://example.com)."]);
});

test("multiline paragraphs and nested lists keep Markdown structure", () => {
  const result = assessmentContent({ recommendation: "**Lưu ý**\nDòng tiếp theo.\n\n- Việc chính\n  - Việc phụ\n- Việc khác", retrieved_context: [] });
  assert.equal(result.actions[0], "**Lưu ý**\nDòng tiếp theo.");
  assert.match(result.actions[1], /Việc chính\n\n- Việc phụ/);
  assert.equal(result.actions[2], "Việc khác");
});

test("a genuinely empty retrieval never fabricates evidence", () => {
  const result = assessmentContent({ recommendation: "Nên theo dõi sức khỏe.", retrieved_context: [] });
  assert.deepEqual(result.evidence, []);
  assert.equal(result.note, "");
});

test("GFM task markers use the interactive checklist instead of leaking raw brackets", () => {
  const result = assessmentContent({ recommendation: "- [ ] **Việc một**\n- [x] Việc hai", retrieved_context: [] });
  assert.deepEqual(result.actions, ["**Việc một**", "Việc hai"]);
});
