#!/usr/bin/env python3
"""Load the bundled Wayfair workbook, prepare context, scan risk, and audit output."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


SKILL_DIR = Path(__file__).resolve().parents[1]
WORKBOOK = SKILL_DIR / "assets" / "wayfair_listing_knowledge_base.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}

REQUIRED_SHEETS = {
    "title_rules": "Wayfair 标题规则",
    "marketing_rules": "Wayfair文案规则",
    "keywords": "关键词（5月数据）",
    "patterns": "Pattern",
    "colors": "Color",
    "decorative": "Decorative Additions装饰其他",
}

TITLE_TAIL = "With Non-Slip Backing"
TITLE_PREFIX = "Machine Washable"
TITLE_MIN_CHARS = 80
TITLE_MAX_CHARS = 220
MARKETING_MIN_WORDS = 75
MARKETING_MAX_WORDS = 100
MARKETING_SENTENCE_COUNT = 5
MARKETING_FIXED_FINAL_SENTENCE = "This rug is ensuring its materials don't contain harmful substances."
MARKETING_SENTENCE_1_INSPIRATION_TERMS = (
    "inspired", "art", "history", "historic", "nature", "natural", "garden",
    "textile", "vintage", "modern", "boho", "safari", "graphic", "motif",
)
MARKETING_SENTENCE_1_LAYOUT_TERMS = (
    "center", "central", "focal", "focus", "framed", "frame", "border",
    "edge", "edges", "field", "across", "surrounding", "outward",
)
MARKETING_SENTENCE_2_TERMS = (
    "faux cashmere", "soft", "velvety", "durable", "surface",
)
MARKETING_SENTENCE_3_TERMS = (
    "machine washable", "machine-washable", "bedroom", "living room",
)
MARKETING_SENTENCE_4_TERMS = (
    "sponge interlayer", "sponge", "non-slip backing", "non slip backing",
    "backing",
)
FEATURE_MIN_COUNT = 6
FEATURE_MAX_COUNT = 6
FEATURE_MIN_WORDS = 5
FEATURE_MAX_WORDS = 30

FIXED_FEATURE_BULLETS = {
    0: "Premium spill-resistant faux cashmere surface prevents liquids and pet accidents from penetrating the fibers",
    1: "The non-slip backing with a sponge interlayer ensures the rug stays firmly in place on the floor, eliminating the need for a separate non-slip pad",
    3: "Machine washable construction allows for a quick refresh to handle real-life household messes",
    4: "Soft low-pile surface resists shedding and daily wear while remaining gentle on feet and paws",
    5: "This area rug is ideal for various settings such as the living room, bedroom, dining room, kitchen, and other high-traffic areas",
}

FEATURE_BULLET_THEME_SEQUENCE = [
    {
        "name": "stain_resistance_or_dirt_handling",
        "terms": (
            "stain", "spill", "liquid", "mess", "dirt", "dust", "vacuum",
            "clean", "accident",
        ),
    },
    {
        "name": "safety_assurance",
        "terms": (
            "non slip", "non-slip", "tpr", "backing", "grip", "stable",
            "floor protection", "floor", "scratch", "noise", "safe",
            "secure", "slip", "sliding", "protect",
        ),
    },
    {
        "name": "visual_design",
        "terms": (
            "pattern", "design", "color", "colors", "motif", "style",
            "zebra", "animal print", "abstract", "floral", "geometric",
            "vintage", "modern", "boho", "border",
        ),
    },
    {
        "name": "washing_convenience",
        "terms": (
            "machine washable", "washable", "wash", "washing", "laundry",
            "cleaning", "rinse", "refresh",
        ),
    },
    {
        "name": "durable_comfort",
        "terms": (
            "soft", "comfort", "comfortable", "low pile", "low-pile",
            "durable", "high traffic", "traffic", "no shedding", "shed",
            "reinforced", "edge", "curling", "vacuum", "thin",
            "low profile",
        ),
    },
    {
        "name": "multi_function_scene_use",
        "terms": (
            "living room", "bedroom", "hallway", "kitchen", "entryway",
            "doorway", "doormat", "runner", "area rug", "dining", "office",
            "laundry", "room", "rooms", "high traffic areas",
        ),
    },
]

TITLE_MAPPING = [
    {
        "slot": "Title1",
        "type": "Doormat",
        "intent": "entryway, doorway, front door, kitchen sink, mudroom, low-door, or small mat placement",
    },
    {
        "slot": "Title2",
        "type": "Hallway Runner",
        "intent": "hallway, corridor, laundry room, kitchen path, or long narrow runner placement",
    },
    {
        "slot": "Title3",
        "type": "Area Rug",
        "intent": "living room, bedroom, dining room, office, nursery, sitting room, or broad room-size placement",
    },
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "into",
    "is", "it", "its", "of", "on", "or", "the", "this", "to", "with", "your",
    "you", "their", "our", "only",
}

LOWERCASE_TITLE_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "nor",
    "of", "on", "or", "the", "to", "with",
}

GENERIC_RUG_ROOTS = {
    "rug", "rugs", "area", "runner", "runners", "carpet", "mat", "doormat",
    "floor", "room", "home", "indoor", "decor",
}

MATERIAL_ROOTS = {
    "wool", "jute", "cotton", "polyester", "sisal", "cashmere", "faux",
    "sponge", "rubber", "latex", "chenille", "viscose",
}

PROHIBITED_TERMS = [
    ("shipping_or_fulfillment", "free shipping", "Shipping promises are not allowed.", "all"),
    ("shipping_or_fulfillment", "fast shipping", "Shipping promises are not allowed.", "all"),
    ("shipping_or_fulfillment", "prime", "Platform fulfillment language is not product copy.", "all"),
    ("warranty_or_guarantee", "warranty", "Warranty or guarantee wording is not title/marketing copy.", "all"),
    ("warranty_or_guarantee", "guarantee", "Warranty or guarantee wording is not title/marketing copy.", "all"),
    ("warranty_or_guarantee", "guaranteed", "Warranty or guarantee wording is not title/marketing copy.", "all"),
    ("ranking_or_superlative", "best on the market", "Unsubstantiated superlative claim.", "all"),
    ("ranking_or_superlative", "highest quality", "Unsubstantiated superlative claim.", "all"),
    ("ranking_or_superlative", "number one", "Unsubstantiated ranking claim.", "all"),
    ("ranking_or_superlative", "#1", "Unsubstantiated ranking claim.", "all"),
    ("ranking_or_superlative", "top rated", "Unsubstantiated ranking claim.", "all"),
    ("promotion_or_price", "cheap", "Price or promotional language is not product copy.", "all"),
    ("promotion_or_price", "discount", "Price or promotional language is not product copy.", "all"),
    ("promotion_or_price", "on sale", "Price or promotional language is not product copy.", "all"),
    ("promotion_or_price", "sale price", "Price or promotional language is not product copy.", "all"),
    ("promotion_or_price", "clearance sale", "Price or promotional language is not product copy.", "all"),
    ("controversial_content", "weapon", "Wayfair title rules flag controversial content.", "all"),
    ("controversial_content", "gun", "Wayfair title rules flag controversial content.", "all"),
    ("controversial_content", "political", "Wayfair title rules flag political content.", "all"),
    ("controversial_content", "religious", "Wayfair title rules flag religious content.", "all"),
    ("controversial_content", "profanity", "Wayfair title rules flag profanity.", "all"),
    ("controversial_content", "sexual", "Wayfair title rules flag sexual content.", "all"),
    ("competitor_or_ip", "rifle paper co", "Competitor or licensed brand term.", "all"),
    ("competitor_or_ip", "loloi", "Competitor or licensed brand term.", "all"),
    ("competitor_or_ip", "safavieh", "Competitor or licensed brand term.", "all"),
    ("competitor_or_ip", "ruggable", "Competitor or licensed brand term.", "all"),
    ("competitor_or_ip", "amber lewis", "Competitor or licensed brand term.", "all"),
    ("competitor_or_ip", "chris loves julia", "Competitor or licensed brand term.", "all"),
]

EVIDENCE_CLAIMS = {
    "machine_washable": ("machine washable", "machine-washable", "washable"),
    "non_slip_backing": ("non slip", "non-slip", "nonslip", "non slip backing", "non-slip backing", "anti slip", "anti-slip"),
    "tpr_backing": ("tpr", "thermoplastic rubber"),
    "faux_cashmere": ("faux cashmere", "cashmere-like", "cashmere flocking"),
    "sponge_layer": ("sponge", "sponge layer", "sponge interlayer"),
    "low_pile": ("low pile", "low-pile"),
    "spill_resistant": ("spill resistant", "spill-resistant", "liquids", "pet accidents"),
    "stain_resistant": ("stain resistant", "stain-resistant", "stain proof", "stain-proof"),
    "pet_household": ("pet", "pets", "paws", "family and pets", "homes with pets"),
    "kids_or_nursery": ("kids", "kid", "children", "child", "nursery", "girl's bedroom", "boys room", "childrens"),
    "outdoor": ("outdoor", "patio", "porch", "deck"),
    "no_harmful_substances": ("no harmful substances", "without harmful substances", "harmful substances", "non toxic", "nontoxic"),
    "waterproof": ("waterproof", "water proof"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(text: object) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = re.sub(r"[\u2010-\u2015_/|]+", " ", text)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff.#]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: object) -> list[str]:
    return [t for t in normalize(text).split() if t and t not in STOPWORDS]


def root_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def roots(text: object) -> set[str]:
    return {root_token(t) for t in tokens(text)}


def cell_col(ref: str) -> int:
    match = re.match(r"[A-Z]+", ref or "")
    if not match:
        return 1
    value = 0
    for char in match.group(0):
        value = value * 26 + ord(char) - 64
    return value


def read_xlsx(path: Path) -> dict[str, list[list[object]]]:
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base not found: {path}")
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iterfind(".//m:t", NS)))

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.get("Id"): rel.get("Target") for rel in rels.findall("r:Relationship", REL_NS)}
        sheets: dict[str, list[list[object]]] = {}
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            name = sheet.get("name") or ""
            rel_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rel_id or "", "").lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            xml = ET.fromstring(zf.read(target))
            rows: list[list[object]] = []
            for row in xml.findall(".//m:sheetData/m:row", NS):
                values: dict[int, object] = {}
                for cell in row.findall("m:c", NS):
                    col = cell_col(cell.get("r") or "")
                    typ = cell.get("t")
                    value_node = cell.find("m:v", NS)
                    inline = cell.find("m:is", NS)
                    value: object = None
                    if typ == "s" and value_node is not None:
                        value = shared[int(value_node.text or "0")]
                    elif typ == "inlineStr" and inline is not None:
                        value = "".join(t.text or "" for t in inline.iterfind(".//m:t", NS))
                    elif value_node is not None:
                        raw = value_node.text or ""
                        try:
                            value = int(raw)
                        except ValueError:
                            try:
                                value = float(raw)
                            except ValueError:
                                value = raw
                    values[col] = value
                max_col = max(values, default=0)
                rows.append([values.get(i) for i in range(1, max_col + 1)])
            sheets[name] = rows
        return sheets


def row_value(row: list[object], idx: int) -> str:
    if idx >= len(row) or row[idx] is None:
        return ""
    return str(row[idx]).strip()


def nonempty_rule_rows(rows: list[list[object]]) -> list[dict]:
    result = []
    for row_num, row in enumerate(rows, start=1):
        values = [str(v).strip() for v in row if v is not None and str(v).strip()]
        if values:
            result.append({"row": row_num, "values": values})
    return result


def load_knowledge() -> dict:
    sheets = read_xlsx(WORKBOOK)
    missing = [name for name in REQUIRED_SHEETS.values() if name not in sheets]
    keywords = []
    for row_num, row in enumerate(sheets.get(REQUIRED_SHEETS["keywords"], [])[1:], start=2):
        category = row_value(row, 0)
        query = row_value(row, 1)
        if not query:
            continue
        raw = row[2] if len(row) > 2 else None
        impressions = None
        if isinstance(raw, (int, float)):
            impressions = float(raw)
        elif raw not in (None, ""):
            try:
                impressions = float(str(raw).replace(",", ""))
            except ValueError:
                impressions = None
        keywords.append({"category": category, "query": query, "impressions": impressions, "row": row_num})

    patterns = []
    for row_num, row in enumerate(sheets.get(REQUIRED_SHEETS["patterns"], [])[1:], start=2):
        value = row_value(row, 0)
        if value:
            patterns.append({"pattern": value, "note": row_value(row, 1), "row": row_num})

    colors = []
    for row_num, row in enumerate(sheets.get(REQUIRED_SHEETS["colors"], [])[1:], start=2):
        value = row_value(row, 0)
        if value:
            colors.append({"color": value, "row": row_num})

    decorative = []
    for row_num, row in enumerate(sheets.get(REQUIRED_SHEETS["decorative"], [])[1:], start=2):
        value = row_value(row, 0)
        if value:
            decorative.append({
                "addition": value,
                "english_note": row_value(row, 1),
                "chinese": row_value(row, 2),
                "chinese_note": row_value(row, 3),
                "row": row_num,
            })

    title_rules = nonempty_rule_rows(sheets.get(REQUIRED_SHEETS["title_rules"], []))
    marketing_rules = nonempty_rule_rows(sheets.get(REQUIRED_SHEETS["marketing_rules"], []))
    status = {
        "ready": not missing and bool(keywords) and bool(patterns) and bool(colors) and bool(title_rules) and bool(marketing_rules),
        "missing_sheets": missing,
        "workbook": WORKBOOK.name,
        "sha256": sha256(WORKBOOK),
        "sheet_names": list(sheets),
        "keyword_count": len(keywords),
        "impressions_count": sum(1 for k in keywords if isinstance(k.get("impressions"), (int, float))),
        "pattern_count": len(patterns),
        "color_count": len(colors),
        "decorative_addition_count": len(decorative),
        "title_rule_count": len(title_rules),
        "marketing_rule_count": len(marketing_rules),
        "static_risk_term_count": len(PROHIBITED_TERMS),
    }
    return {
        "status": status,
        "keywords": keywords,
        "patterns": patterns,
        "colors": colors,
        "decorative": decorative,
        "title_rules": title_rules,
        "marketing_rules": marketing_rules,
    }


def term_matches(text_roots: list[str], term: str) -> bool:
    term_roots = [root_token(t) for t in tokens(term)]
    if not term_roots:
        return False
    if len(term_roots) == 1:
        return term_roots[0] in text_roots
    return f" {' '.join(term_roots)} " in f" {' '.join(text_roots)} "


def split_terms(value: str | None) -> list[str]:
    if not value:
        return []
    return [term.strip() for term in re.split(r"[,;\n]+", value) if term.strip()]


def scan_text(text: str, brand_terms: list[str] | None = None, output: bool = False) -> dict:
    text_roots = [root_token(t) for t in tokens(text)]
    hits = []
    for category, term, reason, scope in PROHIBITED_TERMS:
        if scope == "output" and not output:
            continue
        if term_matches(text_roots, term):
            hits.append({
                "category": category,
                "action": "BLOCK",
                "matched_term_hash": hashlib.sha256(normalize(term).encode()).hexdigest()[:12],
                "reason": reason,
            })
    if output:
        for term in brand_terms or []:
            if term and term_matches(text_roots, term):
                hits.append({
                    "category": "supplier_or_brand_name",
                    "action": "BLOCK",
                    "matched_term_hash": hashlib.sha256(normalize(term).encode()).hexdigest()[:12],
                    "reason": "Supplier/brand names must not appear in final Wayfair copy.",
                })
    unique = {(h["category"], h["matched_term_hash"]): h for h in hits}
    values = list(unique.values())
    return {"pass": not values, "hit_count": len(values), "hits": values}


def evidence_flags(text: str) -> dict[str, bool]:
    text_norm = normalize(text)
    return {
        claim: any(normalize(v) in text_norm for v in variants)
        for claim, variants in EVIDENCE_CLAIMS.items()
    }


def score_library_terms(items: list[dict], field: str, text: str, limit: int) -> list[dict]:
    input_roots = roots(text)
    selected = []
    for item in items:
        value = item[field]
        value_roots = roots(value)
        overlap = input_roots & value_roots
        if not overlap:
            continue
        score = min(100, len(overlap) * 45 + (20 if normalize(value) in normalize(text) else 0))
        selected.append({**item, "relevance_score": score})
    selected.sort(key=lambda x: (-x["relevance_score"], x.get("row", math.inf)))
    return selected[:limit]


def condition_keyword(keyword: str, input_text: str, flags: dict[str, bool]) -> tuple[bool, str]:
    keyword_roots = roots(keyword)
    input_roots = roots(input_text)
    if keyword_roots & {"outdoor", "patio", "porch", "deck"} and not flags.get("outdoor"):
        return False, "outdoor_or_patio_keyword_without_current_evidence"
    if keyword_roots & {"kid", "kids", "child", "children", "nursery"} and not flags.get("kids_or_nursery"):
        return False, "kids_or_nursery_keyword_without_current_evidence"
    if keyword_roots & {"round", "circle"} and not (keyword_roots & input_roots):
        return False, "shape_keyword_without_current_evidence"
    if keyword_roots & MATERIAL_ROOTS and not (keyword_roots & input_roots):
        return False, "material_keyword_without_current_evidence"
    return True, ""


def keyword_retrieval(knowledge: dict, text: str, top: int) -> list[dict]:
    flags = evidence_flags(text)
    input_roots = roots(text)
    selected = []
    for kw in knowledge["keywords"]:
        query = kw["query"]
        if not scan_text(query, output=True)["pass"]:
            continue
        ok, reason = condition_keyword(query, text, flags)
        if not ok:
            continue
        query_roots = roots(query)
        overlap = input_roots & query_roots
        category_match = bool(query_roots & {"rug", "runner", "doormat", "mat", "carpet"})
        specific_roots = query_roots - GENERIC_RUG_ROOTS
        evidence_match = len(overlap) / max(1, len(query_roots))
        relevance = min(100.0, len(overlap) * 22 + evidence_match * 55 + (18 if category_match else 0))
        if specific_roots and not (specific_roots & input_roots):
            relevance -= 18
        if relevance < 18:
            continue
        selected.append({
            **kw,
            "relevance_score": round(max(0.0, min(100.0, relevance)), 2),
            "condition_note": reason,
        })
    selected.sort(key=lambda x: (-x["relevance_score"], -(x["impressions"] or 0), x["row"]))
    return selected[:top]


def read_text_arg(args) -> str:
    if getattr(args, "text_file", None):
        return Path(args.text_file).read_text(encoding="utf-8")
    return getattr(args, "text", "") or ""


def write_json(data: dict, output: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def command_status(args) -> int:
    knowledge = load_knowledge()
    write_json({"knowledge_status": knowledge["status"]}, args.output)
    return 0 if knowledge["status"]["ready"] else 1


def command_scan(args) -> int:
    knowledge = load_knowledge()
    scan = scan_text(read_text_arg(args), split_terms(args.brand), output=args.output_mode)
    write_json({"knowledge_status": knowledge["status"], "scan": scan}, args.output)
    return 0 if scan["pass"] and knowledge["status"]["ready"] else 2


def command_prepare(args) -> int:
    knowledge = load_knowledge()
    text = read_text_arg(args)
    brand_terms = split_terms(args.brand)
    flags = evidence_flags(text)
    input_scan = scan_text(text, brand_terms, output=False)
    needs_confirmation = []
    if not flags.get("machine_washable"):
        needs_confirmation.append("Machine washable must be confirmed because it is fixed in every title.")
    if not flags.get("non_slip_backing"):
        needs_confirmation.append("Non-slip backing must be confirmed because it is fixed in every title.")
    patterns = score_library_terms(knowledge["patterns"], "pattern", text, 10)
    colors = score_library_terms(knowledge["colors"], "color", text, 3)
    if not patterns:
        needs_confirmation.append("Select exactly one workbook Pattern from image/product evidence.")
    if not colors:
        needs_confirmation.append("Select one to three workbook Colors from image/product evidence.")
    result = {
        "knowledge_status": knowledge["status"],
        "brand_terms_to_exclude": brand_terms,
        "input_scan": input_scan,
        "evidence_flags": flags,
        "selected_patterns": patterns,
        "selected_colors": colors,
        "selected_decorative_additions": score_library_terms(knowledge["decorative"], "addition", text, 8),
        "selected_keywords": keyword_retrieval(knowledge, text, args.top),
        "title_type_mapping": TITLE_MAPPING,
        "generation_rules": {
            "title_prefix": TITLE_PREFIX,
            "title_tail": TITLE_TAIL,
            "title_tail_rule": "No word, punctuation, scenario, size, or extra phrase may appear after With Non-Slip Backing.",
            "title_structure": "Machine Washable + Pattern + Color + Product Type + With Non-Slip Backing",
            "tpr_usage_rule": "Mention TPR only when the current product input explicitly confirms TPR backing; otherwise use non-slip backing.",
            "title_chars": [TITLE_MIN_CHARS, TITLE_MAX_CHARS],
            "marketing_copy_words": [MARKETING_MIN_WORDS, MARKETING_MAX_WORDS],
            "marketing_copy_sentence_count": MARKETING_SENTENCE_COUNT,
            "marketing_copy_structure": [
                "Sentence 1: image-based style, Pattern, Colors, inspiration, and visual layout from dominant focus to surrounding field/edges",
                "Sentence 2: faux cashmere surface touch, durable use, and soft/velvety comfort",
                "Sentence 3: machine washable convenience plus bedroom and living room scenes",
                "Sentence 4: sponge interlayer non-slip backing construction",
                f"Sentence 5 fixed: {MARKETING_FIXED_FINAL_SENTENCE}",
            ],
            "feature_bullet_count": [FEATURE_MIN_COUNT, FEATURE_MAX_COUNT],
            "feature_bullet_words": [FEATURE_MIN_WORDS, FEATURE_MAX_WORDS],
            "feature_bullet_fixed_lines": FIXED_FEATURE_BULLETS,
            "feature_bullet_variable_line": {
                "index": 2,
                "theme": "visual_design",
                "structure": "[Current motif/pattern] in [current colors] adds [current style or design effect] to any interior space",
            },
            "final_output_template": [
                "Title1:",
                "Title2:",
                "Title3:",
                "Marketing Copy:",
                "Feature Bullets:",
                "Keyword / Attribute Usage Summary: Pattern&Colors",
                "Blocked Input / Risk Screening:",
                "Wayfair Audit:",
            ],
        },
        "needs_confirmation": needs_confirmation,
    }
    write_json(result, args.output)
    ok = knowledge["status"]["ready"] and input_scan["pass"] and not needs_confirmation
    return 0 if ok else 2


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text))


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.findall(r"[^.!?]+[.!?]", text.strip()) if s.strip()]


def contains_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    text_norm = f" {normalize(text)} "
    return any(f" {normalize(phrase)} " in text_norm for phrase in phrases if normalize(phrase))


def contains_all_phrase_groups(text: str, groups: list[tuple[str, ...]]) -> bool:
    return all(contains_any_phrase(text, group) for group in groups)


def theme_matches(text: str, terms: tuple[str, ...]) -> bool:
    text_norm = f" {normalize(text)} "
    text_roots = roots(text)
    for term in terms:
        term_norm = normalize(term)
        if not term_norm:
            continue
        if " " in term_norm:
            if f" {term_norm} " in text_norm:
                return True
        elif root_token(term_norm) in text_roots:
            return True
    return False


def title_case_issues(title: str) -> list[str]:
    issues = []
    for word in re.findall(r"[A-Za-z][A-Za-z-]*", title):
        for part in [p for p in word.split("-") if p]:
            if part.lower() in LOWERCASE_TITLE_WORDS:
                continue
            if not part[0].isupper():
                issues.append(word)
                break
    return sorted(set(issues))


def title_colors(title: str, colors: list[dict]) -> list[str]:
    title_norm = normalize(title)
    found = []
    for item in colors:
        color = item["color"]
        if re.search(rf"\b{re.escape(normalize(color))}\b", title_norm):
            found.append(color)
    return found


def title_has_pattern(title: str, patterns: list[dict], listing_pattern: str | None) -> bool:
    title_norm = normalize(title)
    if listing_pattern and normalize(listing_pattern) in title_norm:
        return True
    return any(normalize(item["pattern"]) in title_norm for item in patterns)


def listing_titles_text(titles: list) -> list[str]:
    result = []
    for item in titles:
        if isinstance(item, dict):
            result.append(str(item.get("title", "")))
        else:
            result.append(str(item))
    return result


def command_audit(args) -> int:
    knowledge = load_knowledge()
    listing = json.loads(Path(args.listing_json).read_text(encoding="utf-8"))
    context = json.loads(Path(args.context_json).read_text(encoding="utf-8"))
    brand_terms = context.get("brand_terms_to_exclude", [])
    selected_patterns = context.get("selected_patterns", [])
    selected_colors = context.get("selected_colors", [])
    flags = context.get("evidence_flags", {})
    listing_pattern = listing.get("pattern")
    listing_colors = listing.get("colors") or []
    if isinstance(listing_colors, str):
        listing_colors = split_terms(listing_colors.replace("/", ","))

    errors = []
    warnings = []
    titles = listing.get("titles", [])
    marketing = str(listing.get("marketing_copy", ""))
    bullets = listing.get("feature_bullets", [])

    if len(titles) != len(TITLE_MAPPING):
        errors.append({"code": "TITLE_COUNT", "module": "titles", "expected": 3, "actual": len(titles)})

    for idx, expected in enumerate(TITLE_MAPPING):
        if idx >= len(titles):
            continue
        item = titles[idx]
        slot = item.get("slot", "") if isinstance(item, dict) else ""
        title_type = item.get("type", "") if isinstance(item, dict) else ""
        title = item.get("title", "") if isinstance(item, dict) else str(item)
        module = f"titles[{idx}]"
        title_norm = normalize(title)
        if slot != expected["slot"]:
            errors.append({"code": "TITLE_SLOT_MISMATCH", "module": module, "expected": expected["slot"], "actual": slot})
        if title_type != expected["type"]:
            errors.append({"code": "TITLE_TYPE_FIELD_MISMATCH", "module": module, "expected": expected["type"], "actual": title_type})
        if expected["type"].lower() not in title.lower():
            errors.append({"code": "TITLE_PRODUCT_TYPE_MISSING", "module": module, "expected": expected["type"]})
        if not title.startswith(TITLE_PREFIX):
            errors.append({"code": "TITLE_PREFIX", "module": module, "expected": TITLE_PREFIX})
        if not title.endswith(TITLE_TAIL):
            errors.append({
                "code": "TITLE_TAIL",
                "module": module,
                "expected": TITLE_TAIL,
                "reason": "Title must end exactly with With Non-Slip Backing and have no words after it.",
            })
        if re.search(rf"{re.escape(TITLE_TAIL)}\s+\S+", title):
            errors.append({"code": "TITLE_WORDS_AFTER_FIXED_TAIL", "module": module})
        if len(title) < TITLE_MIN_CHARS or len(title) > TITLE_MAX_CHARS:
            errors.append({"code": "TITLE_LENGTH", "module": module, "value": len(title), "expected": [TITLE_MIN_CHARS, TITLE_MAX_CHARS]})
        if selected_patterns and not title_has_pattern(title, selected_patterns, listing_pattern):
            errors.append({"code": "TITLE_PATTERN_MISSING", "module": module})
        found_colors = title_colors(title, knowledge["colors"])
        if not found_colors:
            errors.append({"code": "TITLE_COLOR_MISSING", "module": module})
        if len(found_colors) > 3:
            errors.append({"code": "TITLE_TOO_MANY_COLORS", "module": module, "colors": found_colors})
        if listing_colors:
            allowed = {normalize(c) for c in listing_colors}
            if not any(normalize(c) in allowed for c in found_colors):
                errors.append({"code": "TITLE_COLOR_NOT_IN_LISTING_COLORS", "module": module, "colors": found_colors})
        elif selected_colors:
            allowed = {normalize(c["color"]) for c in selected_colors}
            if not any(normalize(c) in allowed for c in found_colors):
                errors.append({"code": "TITLE_COLOR_NOT_SELECTED", "module": module, "colors": found_colors})
        if has_cjk(title):
            errors.append({"code": "TITLE_LANGUAGE", "module": module})
        letters = re.findall(r"[A-Za-z]", title)
        if letters and sum(1 for ch in letters if ch.isupper()) / len(letters) > 0.85:
            errors.append({"code": "TITLE_ALL_CAPS", "module": module})
        case_issues = title_case_issues(title)
        if case_issues:
            errors.append({"code": "TITLE_CASE", "module": module, "words": case_issues[:10]})
        type_pos = title.lower().find(expected["type"].lower())
        if len(title) > 70 and type_pos >= 70:
            warnings.append({"code": "TITLE_TYPE_AFTER_FIRST_70_CHARS", "module": module, "expected": expected["type"]})

    marketing_words = word_count(marketing)
    if not MARKETING_MIN_WORDS <= marketing_words <= MARKETING_MAX_WORDS:
        errors.append({"code": "MARKETING_COPY_WORDS", "module": "marketing_copy", "value": marketing_words, "expected": [MARKETING_MIN_WORDS, MARKETING_MAX_WORDS]})
    if "\n" in marketing.strip():
        errors.append({"code": "MARKETING_COPY_PARAGRAPH", "module": "marketing_copy"})
    if len(marketing.strip()) < 15:
        errors.append({"code": "MARKETING_COPY_TOO_SHORT", "module": "marketing_copy"})
    if has_cjk(marketing):
        errors.append({"code": "MARKETING_COPY_LANGUAGE", "module": "marketing_copy"})
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:x|by)\s*\d+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\s?(?:inch|inches|ft|feet|cm)\b", marketing, re.I):
        errors.append({"code": "MARKETING_COPY_OPTION_SPECIFIC_SIZE", "module": "marketing_copy"})
    marketing_sentences = split_sentences(marketing)
    if len(marketing_sentences) != MARKETING_SENTENCE_COUNT:
        errors.append({
            "code": "MARKETING_COPY_SENTENCE_COUNT",
            "module": "marketing_copy",
            "value": len(marketing_sentences),
            "expected": MARKETING_SENTENCE_COUNT,
        })
    if len(marketing_sentences) >= 1:
        s1 = marketing_sentences[0]
        if selected_patterns and not any(normalize(item["pattern"]) in normalize(s1) for item in selected_patterns):
            errors.append({"code": "MARKETING_COPY_S1_PATTERN", "module": "marketing_copy"})
        s1_colors = title_colors(s1, knowledge["colors"])
        if len(s1_colors) < 1:
            errors.append({"code": "MARKETING_COPY_S1_COLORS", "module": "marketing_copy"})
        if not contains_any_phrase(s1, MARKETING_SENTENCE_1_INSPIRATION_TERMS):
            errors.append({"code": "MARKETING_COPY_S1_INSPIRATION", "module": "marketing_copy"})
        if not contains_any_phrase(s1, MARKETING_SENTENCE_1_LAYOUT_TERMS):
            errors.append({"code": "MARKETING_COPY_S1_VISUAL_LAYOUT", "module": "marketing_copy"})
    if len(marketing_sentences) >= 2:
        if not contains_all_phrase_groups(marketing_sentences[1], [
            ("faux cashmere",),
            ("soft", "velvety"),
            ("durable", "daily", "wear"),
        ]):
            errors.append({"code": "MARKETING_COPY_S2_TOUCH", "module": "marketing_copy"})
    if len(marketing_sentences) >= 3:
        if not contains_all_phrase_groups(marketing_sentences[2], [
            ("machine washable", "machine-washable"),
            ("bedroom", "bedrooms"),
            ("living room", "living rooms"),
        ]):
            errors.append({"code": "MARKETING_COPY_S3_WASH_SCENES", "module": "marketing_copy"})
    if len(marketing_sentences) >= 4:
        if not contains_all_phrase_groups(marketing_sentences[3], [
            ("sponge interlayer", "sponge"),
            ("non-slip backing", "non slip backing"),
        ]):
            errors.append({"code": "MARKETING_COPY_S4_BACKING", "module": "marketing_copy"})
        if re.search(r"\btpr\b", marketing_sentences[3], re.I) and not flags.get("tpr_backing", False):
            errors.append({"code": "UNSUPPORTED_CLAIM", "module": "marketing_copy", "claim_category": "tpr_backing"})
    if len(marketing_sentences) >= 5:
        if marketing_sentences[4] != MARKETING_FIXED_FINAL_SENTENCE:
            errors.append({
                "code": "MARKETING_COPY_FIXED_FINAL_SENTENCE",
                "module": "marketing_copy",
                "expected": MARKETING_FIXED_FINAL_SENTENCE,
            })

    if not isinstance(bullets, list):
        errors.append({"code": "FEATURE_BULLETS_TYPE", "module": "feature_bullets"})
        bullets = []
    if not FEATURE_MIN_COUNT <= len(bullets) <= FEATURE_MAX_COUNT:
        errors.append({"code": "FEATURE_BULLET_COUNT", "module": "feature_bullets", "value": len(bullets), "expected": [FEATURE_MIN_COUNT, FEATURE_MAX_COUNT]})
    marketing_norm = normalize(marketing)
    for idx, bullet in enumerate(bullets):
        bullet_text = str(bullet)
        module = f"feature_bullets[{idx}]"
        wc = word_count(bullet_text)
        if not FEATURE_MIN_WORDS <= wc <= FEATURE_MAX_WORDS:
            errors.append({"code": "FEATURE_BULLET_WORDS", "module": module, "value": wc, "expected": [FEATURE_MIN_WORDS, FEATURE_MAX_WORDS]})
        if re.search(r"[.!?;:]\s*$", bullet_text):
            errors.append({"code": "FEATURE_BULLET_PUNCTUATION", "module": module})
        if has_cjk(bullet_text):
            errors.append({"code": "FEATURE_BULLET_LANGUAGE", "module": module})
        if normalize(bullet_text) and normalize(bullet_text) in marketing_norm:
            errors.append({"code": "FEATURE_BULLET_DUPLICATES_MARKETING_COPY", "module": module})
        fixed_text = FIXED_FEATURE_BULLETS.get(idx)
        if fixed_text is not None:
            if bullet_text != fixed_text:
                errors.append({
                    "code": "FEATURE_BULLET_FIXED_TEXT",
                    "module": module,
                    "expected": fixed_text,
                })
        elif idx == 2:
            theme = FEATURE_BULLET_THEME_SEQUENCE[2]
            if not theme_matches(bullet_text, theme["terms"]):
                errors.append({
                    "code": "FEATURE_BULLET_IMAGE_LINE",
                    "module": module,
                    "expected_theme": theme["name"],
                })

    all_text = "\n".join(listing_titles_text(titles) + [marketing] + [str(b) for b in bullets])
    risk = scan_text(all_text, brand_terms, output=True)
    if not risk["pass"]:
        errors.append({"code": "RISK_TERM", "module": "listing", "categories": sorted({h["category"] for h in risk["hits"]})})
    if re.search(r"https?://|www\.", all_text, re.I):
        errors.append({"code": "URL", "module": "listing"})
    if re.search(r"<[^>]+>", all_text):
        errors.append({"code": "HTML", "module": "listing"})

    claim_scan_parts = listing_titles_text(titles) + [marketing]
    if isinstance(bullets, list) and len(bullets) > 2:
        claim_scan_parts.append(str(bullets[2]))
    listing_norm = normalize("\n".join(claim_scan_parts))
    operator_fixed_marketing_claims = {"faux_cashmere", "sponge_layer", "no_harmful_substances"}
    for claim, variants in EVIDENCE_CLAIMS.items():
        if claim in operator_fixed_marketing_claims:
            continue
        present = any(normalize(v) in listing_norm for v in variants)
        if present and not flags.get(claim, False):
            errors.append({"code": "UNSUPPORTED_CLAIM", "module": "listing", "claim_category": claim})
    if not context.get("knowledge_status", {}).get("ready"):
        errors.append({"code": "KB_MISSING", "module": "context"})

    result = {
        "knowledge_status": knowledge["status"],
        "release_status": "PASS" if not errors else "REWRITE",
        "errors": errors,
        "warnings": warnings,
        "risk_scan": risk,
        "metrics": {
            "title_count": len(titles),
            "title_lengths": [len(t) for t in listing_titles_text(titles)],
            "marketing_copy_words": marketing_words,
            "feature_bullet_count": len(bullets),
            "feature_bullet_words": [word_count(str(b)) for b in bullets],
        },
    }
    write_json(result, args.output)
    return 0 if not errors else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Validate and summarize the bundled workbook")
    status.add_argument("--output")
    status.set_defaults(func=command_status)

    scan = sub.add_parser("scan", help="Scan text against Wayfair risk rules")
    group = scan.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--text-file")
    scan.add_argument("--brand", default="")
    scan.add_argument("--output-mode", action="store_true")
    scan.add_argument("--output")
    scan.set_defaults(func=command_scan)

    prepare = sub.add_parser("prepare", help="Load knowledge and retrieve current-product context")
    group = prepare.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--text-file")
    prepare.add_argument("--brand", default="")
    prepare.add_argument("--top", type=int, default=120)
    prepare.add_argument("--output")
    prepare.set_defaults(func=command_prepare)

    audit = sub.add_parser("audit", help="Audit generated Wayfair Listing JSON")
    audit.add_argument("--listing-json", required=True)
    audit.add_argument("--context-json", required=True)
    audit.add_argument("--output")
    audit.set_defaults(func=command_audit)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, KeyError, ValueError, zipfile.BadZipFile, json.JSONDecodeError, ET.ParseError) as exc:
        print(json.dumps({"error": str(exc), "release_status": "BLOCKED"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
