"""Pipeline nạp tri thức: web/PDF -> đoạn bằng chứng -> Neo4j, không qua tệp JSON trung gian.

Đọc data/corpus/sources.json (danh sách nguồn) và data/corpus/graph.json (thực thể/quan hệ
viết tay, trỏ tới evidence id), tải từng nguồn (cache HTML/PDF ở data/corpus/.cache), làm sạch,
chia đoạn, ghép thành KB trong bộ nhớ, kiểm tra nhất quán rồi MERGE thẳng vào Neo4j.

Dùng:
  python scripts/collect_corpus.py                       # tải + xử lý + nạp Neo4j
  python scripts/collect_corpus.py --dry-run             # chỉ xử lý và kiểm tra
  python scripts/collect_corpus.py --only who-diabetes   # thử một nguồn, không nạp
"""

import argparse
import datetime
import json
import re
import sys
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import get_settings  # noqa: E402
from tools.neo4j_kb import KnowledgeBaseError, KnowledgeGraph, create_driver, validate_kb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"
CACHE_DIR = CORPUS_DIR / ".cache"
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
    parser.add_argument("--only", nargs="*", help="chỉ xử lý các source id này (không nạp Neo4j)")
    parser.add_argument("--dry-run", action="store_true", help="xử lý và kiểm tra, không nạp Neo4j")
    args = parser.parse_args()

    manifest = json.loads((CORPUS_DIR / "sources.json").read_text(encoding="utf-8"))
    sources = [s for s in manifest["sources"] if not args.only or s["id"] in args.only]

    passages, failed = [], []
    for source in sources:
        try:
            found = process(source)
            if not found:
                raise ValueError("không trích được nội dung")
        except Exception as exc:  # một nguồn lỗi không làm hỏng cả corpus
            failed.append(source["id"])
            print(f"[LỖI] {source['id']}: {exc}", file=sys.stderr)
            continue
        print(f"[OK ] {source['id']:<30} {len(found):>3} đoạn")
        passages.extend(found)

    # Nạp thiếu nguồn rồi prune sẽ xóa dữ liệu cũ của nguồn lỗi, nên dừng sớm.
    if args.only or failed or not passages:
        print("Không nạp Neo4j (chạy một phần, có nguồn lỗi hoặc không có dữ liệu).", file=sys.stderr)
        return 1 if failed or not passages else 0

    graph = json.loads((CORPUS_DIR / "graph.json").read_text(encoding="utf-8"))
    kb = {
        "version": "corpus-" + datetime.date.today().isoformat(),
        "sources": [{k: s[k] for k in ("id", "title", "publisher", "year", "url") if k in s} for s in sources],
        "entities": graph["entities"],
        "evidence": [{k: p[k] for k in ("id", "source", "section", "text")} for p in passages],
        "relations": graph["relations"],
    }
    try:
        validate_kb(kb)  # evidence id trong graph.json phải còn tồn tại sau khi chia đoạn
    except KnowledgeBaseError as exc:
        print(f"[LỖI] KB không hợp lệ: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"KB hợp lệ: {len(passages)} đoạn. --dry-run: không nạp Neo4j.")
        return 0

    settings = get_settings()
    driver = create_driver(settings)
    try:
        graph_db = KnowledgeGraph(driver, settings.neo4j_database)
        graph_db.load(kb)
        print("Đã nạp vào Neo4j:", graph_db.stats())
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
