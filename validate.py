"""校验 seed_data.py 的数据完整性，改完数据后、push 前运行：

    python validate.py

全部通过输出 OK；有问题会逐条列出并以非零码退出。
"""
import re
import sys

from seed_data import CASES, GLOSSARY

REQUIRED_FIELDS = [
    "archive_no", "name", "aliases", "period", "era", "region", "year_start",
    "location", "case_type", "credibility", "symbol", "summary",
    "case_details", "timeline", "psychological_profile", "terms", "sources",
]

KNOWN_SYMBOLS = {
    "tower", "envelope", "gun", "road", "flame",
    "tape", "house", "camera", "shovel", "poison",
}

errors = []


def err(msg):
    errors.append(msg)


glossary_ids = [g["id"] for g in GLOSSARY]
if len(glossary_ids) != len(set(glossary_ids)):
    err("GLOSSARY 中存在重复的 id")
for g in GLOSSARY:
    for field in ("id", "term", "term_en", "definition"):
        if not g.get(field):
            err(f"词条 {g.get('id', '?')} 缺少字段 {field}")

archive_nos = []
for i, case in enumerate(CASES):
    label = case.get("archive_no") or case.get("name") or f"第{i + 1}条"

    for field in REQUIRED_FIELDS:
        if field not in case:
            err(f"{label}: 缺少字段 {field}")
        elif case[field] in ("", None):
            err(f"{label}: 字段 {field} 为空")

    no = case.get("archive_no", "")
    if no:
        archive_nos.append(no)
        if not re.fullmatch(r"HR-\d{3}", no):
            err(f"{label}: archive_no 格式应为 HR-三位数字，当前为 {no!r}")

    year = case.get("year_start")
    if year is not None and (not isinstance(year, int) or not 1000 <= year <= 2100):
        err(f"{label}: year_start 应为四位年份整数，当前为 {year!r}")

    symbol = case.get("symbol")
    if symbol and symbol not in KNOWN_SYMBOLS:
        err(f"{label}: 未知符号 {symbol!r}，可选值：{sorted(KNOWN_SYMBOLS)}")

    timeline = case.get("timeline")
    if timeline is not None:
        if not isinstance(timeline, list) or not timeline:
            err(f"{label}: timeline 应为非空列表")
        else:
            for item in timeline:
                if not (isinstance(item, (list, tuple)) and len(item) == 2
                        and all(isinstance(part, str) and part for part in item)):
                    err(f"{label}: timeline 条目应为 (时间, 事件) 二元组，当前为 {item!r}")

    terms = case.get("terms")
    if terms is not None:
        if not isinstance(terms, list):
            err(f"{label}: terms 应为列表")
        else:
            for t in terms:
                if t not in glossary_ids:
                    err(f"{label}: terms 引用了不存在的词条 id {t!r}")

if len(archive_nos) != len(set(archive_nos)):
    err("存在重复的 archive_no")

if errors:
    print(f"校验失败，共 {len(errors)} 个问题：\n")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)

print(f"OK — {len(CASES)} 份档案、{len(GLOSSARY)} 个词条全部通过校验。")
