"""Thu thập tài liệu y khoa về đái tháo đường (web + PDF) thành corpus dạng KB.

Đọc data/corpus/sources.json, tải từng nguồn (cache ở data/corpus/.cache), làm sạch,
chia thành các đoạn (passage) và ghi:

  data/corpus/passages.jsonl    mỗi dòng một đoạn: id, source, section, text, lang
  data/corpus/corpus_kb.json    cùng schema với data/kb/diabetes_kb.json
                                (sources + evidence từ các đoạn trên,
                                entities + relations từ data/corpus/graph.json)

Dùng:
  python scripts/collect_corpus.py                 # tải + xử lý tất cả nguồn
  python scripts/collect_corpus.py --only who-diabetes
  python scripts/collect_corpus.py --install       # ghi đè data/kb/diabetes_kb.json (có sao lưu)
"""

import argparse
import json
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.neo4j_kb import KnowledgeBaseError, validate_kb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"
CACHE_DIR = CORPUS_DIR / ".cache"
KB_PATH = ROOT / "data" / "kb" / "diabetes_kb.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (healthcare-agent-system corpus collector; educational use)"}
TIMEOUT = 60

MIN_CHARS = 150  # đoạn ngắn hơn sẽ được gộp vào đoạn kế
TARGET_CHARS = 700  # độ dài đoạn mong muốn
MAX_CHARS = 1100  # đoạn dài hơn sẽ bị tách theo câu

# Dòng quảng cáo / điều hướng của trang web, loại bỏ khỏi nội dung.
NOISE_LINE = re.compile(
    r"(đặt lịch|đặt hẹn|hotline|liên hệ|xem thêm|bài viết liên quan|tải app|fanpage|"
    r"gói (khám|tầm soát)|vinmec (là|có|cung cấp)|trung tâm tiêm chủng|follow|subscribe|"
    r"share (this|on)|cookie|read more|related (articles|topics)|"
    r"bài viết (này )?được (viết|tham vấn|tư vấn)|tham vấn chuyên môn|tư vấn chuyên môn)",
    re.IGNORECASE,
)
# Từ khóa đánh dấu phần cuối bài (tài liệu tham khảo, kêu gọi đặt lịch...).
END_MARKERS = re.compile(
    r"^(tài liệu tham khảo|nguồn tham khảo|nguồn:|references?|để đặt lịch)",
    re.IGNORECASE,
)


def fetch(url, cache_name, binary=False):
    """Tải url, dùng cache nếu có. Có kiểm tra TLS đầy đủ."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / cache_name
    if path.exists() and path.stat().st_size:
        return path.read_bytes() if binary else path.read_text(encoding="utf-8")
    parts = urllib.parse.urlsplit(url)
    safe = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, urllib.parse.quote(parts.path), parts.query, "")
    )
    response = requests.get(safe, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    if binary:
        path.write_bytes(response.content)
        return response.content
    response.encoding = response.apparent_encoding if not response.encoding else response.encoding
    path.write_text(response.text, encoding="utf-8")
    return response.text


def clean_text(text):
    text = text.replace(" ", " ").replace("​", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def web_blocks(html, selector=None):
    """Trả về danh sách (kind, text) với kind là 'h' (tiêu đề) hoặc 'p' (đoạn văn)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()
    root = None
    for candidate in filter(None, [selector, "div.detail-content", "article", "main"]):
        root = soup.select_one(candidate)
        if root and len(root.get_text(strip=True)) > 500:
            break
        root = None
    root = root or soup.body
    blocks = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
        if el.name != "tr" and el.find_parent("table"):
            continue  # nội dung bảng đã được đọc theo từng hàng
        if el.name == "p" and el.find_parent("li"):
            continue  # đã nằm trong mục danh sách
        if el.name == "tr":
            cells = [clean_text(c.get_text(" ", strip=True)) for c in el.find_all(["th", "td"])]
            text = " | ".join(c for c in cells if c)
            kind = "p" if len(cells) > 1 else None
            if kind and text:
                blocks.append(("t", text))
            continue
        text = clean_text(el.get_text(" ", strip=True))
        if not text:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            blocks.append(("h", text))
        elif el.name == "li":
            blocks.append(("li", text))
        else:
            blocks.append(("p", text))
    return merge_lists(blocks)


def merge_lists(blocks):
    """Gộp các mục danh sách liên tiếp (vd triệu chứng) thành một khối, nối vào câu dẫn nếu có."""
    merged, items = [], []

    def flush_items():
        if not items:
            return
        joined = "; ".join(items)
        if merged and merged[-1][0] == "p" and merged[-1][1].rstrip().endswith(":"):
            merged[-1] = ("p", f"{merged[-1][1]} {joined}.")
        else:
            merged.append(("p", joined + "."))
        items.clear()

    for kind, text in blocks:
        if kind == "li":
            items.append(text.rstrip(".;"))
        else:
            flush_items()
            # hàng bảng: giữ nguyên là một đoạn riêng, không gộp với đoạn khác
            merged.append(("p", text) if kind == "t" else (kind, text))
    flush_items()
    return merged


def pdf_blocks(data):
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    blocks = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        # PDF ngắt dòng cứng: nối các dòng thuộc cùng một đoạn.
        paragraph = []
        for line in raw.splitlines():
            line = clean_text(line)
            if not line or re.fullmatch(r"[_\-\d\s]+", line):
                if paragraph:
                    blocks.append(("p", " ".join(paragraph)))
                    paragraph = []
                continue
            paragraph.append(line)
            if re.search(r"[.:;]$", line) and len(line) < 60:
                blocks.append(("p", " ".join(paragraph)))
                paragraph = []
        if paragraph:
            blocks.append(("p", " ".join(paragraph)))
    return blocks


def split_long(text):
    """Tách đoạn quá dài theo câu, không cắt giữa số/đơn vị (vd 6,5%, 126 mg/dL)."""
    sentences = re.split(r"(?<=[.!?;])\s+(?=[A-ZÀ-Ỹ0-9•\-])", text)
    chunks, current = [], ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > TARGET_CHARS:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


# Câu quảng cáo dịch vụ hoặc tiểu sử tác giả: bỏ từng câu, giữ phần y khoa còn lại trong đoạn.
PROMO_SENTENCE = re.compile(
    r"(vinmec|gói (sàng lọc|khám|dịch vụ)|"
    r"(thạc sĩ|tiến sĩ|ths|ts)\.?\s*,?\s*(bác sĩ|bs)|bài viết (được )?(bởi|tham khảo)|"
    r"kinh nghiệm (trong|làm việc)|hội thảo trong|"
    r"thảo dược|sản phẩm hỗ trợ kiểm soát)",
    re.IGNORECASE,
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÀ-Ỹ0-9•\-])")
HEADER_BOILERPLATE = re.compile(
    r"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\s*Độc lập\s*-\s*Tự do\s*-\s*Hạnh phúc\s*"
)


def strip_promo(text):
    text = HEADER_BOILERPLATE.sub("", text)
    kept = [x for x in SENTENCE_SPLIT.split(text) if not PROMO_SENTENCE.search(x)]
    return " ".join(kept).strip()


def to_passages(blocks):
    """Gộp các khối thành passage kèm tên mục (heading gần nhất)."""
    cleaned, section = [], ""
    for kind, text in blocks:
        if kind == "h":
            if END_MARKERS.match(text.lower()):
                break
            section = text
            continue
        if END_MARKERS.match(text.lower()):
            break
        if NOISE_LINE.search(text) and len(text) < 220:
            continue
        text = strip_promo(text)
        if len(text) < 25:
            continue
        cleaned.append((section, text))

    passages, buffer, buffer_section = [], "", ""

    def flush():
        nonlocal buffer, buffer_section
        if len(buffer) >= MIN_CHARS or (buffer and not passages):
            passages.append((buffer_section, buffer))
        elif buffer and passages:
            prev_section, prev_text = passages[-1]
            passages[-1] = (prev_section, f"{prev_text} {buffer}")
        buffer, buffer_section = "", ""

    for section, text in cleaned:
        if buffer and (section != buffer_section or len(buffer) >= TARGET_CHARS):
            flush()
        buffer_section = buffer_section or section
        buffer = f"{buffer} {text}".strip()
    flush()

    result = []
    for section, text in passages:
        pieces = split_long(text) if len(text) > MAX_CHARS else [text]
        result.extend((section, piece) for piece in pieces)
    return result


def process(source):
    cache_ext = "pdf" if source["type"] == "pdf" else "html"
    cache_name = f"{source['id']}.{cache_ext}"
    if source["type"] == "pdf":
        blocks = pdf_blocks(fetch(source["url"], cache_name, binary=True))
    else:
        blocks = web_blocks(fetch(source["url"], cache_name), source.get("selector"))
    passages = to_passages(blocks)
    return [
        {
            "id": f"ev-{source['id']}-{index:03d}",
            "source": source["id"],
            "section": section or source["title"],
            "text": text,
            "lang": source["lang"],
        }
        for index, (section, text) in enumerate(passages, start=1)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--only", nargs="*", help="chỉ xử lý các source id này")
    parser.add_argument("--install", action="store_true", help="ghi đè data/kb/diabetes_kb.json (có sao lưu)")
    args = parser.parse_args()

    manifest = json.loads((CORPUS_DIR / "sources.json").read_text(encoding="utf-8"))
    sources = [s for s in manifest["sources"] if not args.only or s["id"] in args.only]

    all_passages, done_sources, failed = [], [], []
    for source in sources:
        try:
            passages = process(source)
        except Exception as exc:  # một nguồn lỗi không làm hỏng cả corpus
            failed.append((source["id"], str(exc)))
            print(f"[LỖI] {source['id']}: {exc}", file=sys.stderr)
            continue
        if not passages:
            failed.append((source["id"], "không trích được nội dung"))
            print(f"[LỖI] {source['id']}: không trích được nội dung", file=sys.stderr)
            continue
        total = sum(len(p["text"]) for p in passages)
        print(f"[OK ] {source['id']:<30} {len(passages):>3} đoạn  {total:>6} ký tự")
        all_passages.extend(passages)
        done_sources.append(source)

    if args.only:
        print("Chạy một phần (--only): không ghi đè corpus.", file=sys.stderr)
        return 1 if failed else 0
    if not all_passages:
        print("Không có dữ liệu nào được thu thập.", file=sys.stderr)
        return 1

    graph = json.loads((CORPUS_DIR / "graph.json").read_text(encoding="utf-8"))
    with (CORPUS_DIR / "passages.jsonl").open("w", encoding="utf-8") as file:
        for passage in all_passages:
            file.write(json.dumps(passage, ensure_ascii=False) + "\n")

    kb = {
        "version": "corpus-" + __import__("datetime").date.today().isoformat(),
        "sources": [
            {k: s[k] for k in ("id", "title", "publisher", "year", "url") if k in s}
            for s in done_sources
        ],
        "entities": graph["entities"],
        "evidence": [
            {k: p[k] for k in ("id", "source", "section", "text")} for p in all_passages
        ],
        "relations": graph["relations"],
    }
    try:
        validate_kb(kb)  # evidence id trong graph.json phải còn tồn tại sau khi chia đoạn
    except KnowledgeBaseError as exc:
        print(f"[LỖI] corpus_kb.json không hợp lệ: {exc}", file=sys.stderr)
        return 1
    (CORPUS_DIR / "corpus_kb.json").write_text(
        json.dumps(kb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nTổng: {len(done_sources)} nguồn, {len(all_passages)} đoạn -> data/corpus/")

    if args.install:
        backup = KB_PATH.with_suffix(".json.bak")
        shutil.copy2(KB_PATH, backup)
        KB_PATH.write_text(json.dumps(kb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Đã ghi đè {KB_PATH.relative_to(ROOT)} (sao lưu: {backup.name})")

    if failed:
        print(f"{len(failed)} nguồn lỗi: " + ", ".join(i for i, _ in failed), file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
