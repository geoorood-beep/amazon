#!/usr/bin/env python3
"""Amazon Listing 四模块校验（标题 / 亮点 / 五点 / 详情）。

用法:
    python3 validate.py input.json          # 人读报告
    python3 validate.py input.json --json   # JSON 报告
退出码: 0 = 无硬性失败; 1 = 有硬性失败; 2 = 输入文件错误。

input.json 结构（示例见 example_input.json）:
{
  "brand": "品牌准确拼写",                 # 可选；标题特殊字符检查时豁免品牌内的字符
  "species": "dog" | "cat" | "both",       # 可选；检查猫狗错路由
  "title": "...",                          # 文本可含 ** 加粗标记
  "highlights": "...",
  "bullets": ["...", "...", "...", "...", "..."],   # 可带 "1." 序号，脚本会去掉
  "description": "段落1\\n\\n段落2",
  "keywords": [                            # 生成前确认的准入词表（分母固定）
    {"phrase": "cat water fountain", "variants": ["cat water fountains"], "core": true},
    "pet water dispenser"                  # 也可直接写字符串
  ],
  "limits": {"title_max": 75}              # 可选；覆盖默认上限
}

字符数口径: 去掉 ** 与首尾空白，保留内部空格/标点/换行，按 Unicode 码点计。
本脚本只做规则复核，不代表亚马逊后台验证通过。
"""
import json
import re
import sys
import unicodedata

LIMITS = {
    "title_max": 75,             # 硬: 见 references/limits.md
    "highlights_max": 125,       # 硬
    "bullet_max": 256,           # 硬（每条）
    "bullets_total_max": 1000,   # 硬: 用户确认
    "description_max": 2000,     # 硬（内部保守值）
    "bullet_count": 5,
    "core_cap_title": 1,         # 核心词在标题最多出现次数
    "core_cap_other": 2,         # 核心词在亮点/五点合计/详情各自最多次数
    "desc_paragraphs_min": 2,
    "desc_paragraphs_max": 4,
}

TITLE_FORBIDDEN = set("!$?_{}^¬¦|")
TITLE_STOPWORDS = {"a", "an", "the", "and", "or", "for", "of", "in", "on",
                   "with", "to", "by", "at", "from", "&", "as", "is"}

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'’][A-Za-z0-9]+)*")

# 硬性失败：促销/价格/评价诱导/外链联系方式
HARD_PATTERNS = [
    (r"\$", "含价格符号 $"),
    (r"\b(?:discount|coupon|limited[- ]time|free shipping|free gift|"
     r"money[- ]back|satisfaction guarantee[d]?|leave (?:us )?a review)\b", "促销/退款/评价诱导类表述"),
    (r"\bbest[- ]?sell(?:er|ing)\b|#\s?1\b|\bnumber one\b|\b(?:5|five)[- ]star\b", "排名/评分类表述"),
    (r"<[a-zA-Z/][^>]*>", "含 HTML 标签"),
    (r"https?://|\bwww\.", "含外链"),
    (r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", "含邮箱"),
]

# 警告：必须对照产品资料核证，无证据就删
EVIDENCE_TERMS = [
    "bpa-free", "bpa free", "food-grade", "food grade", "non-toxic", "nontoxic",
    "antibacterial", "anti-bacterial", "antimicrobial", "hypoallergenic", "fda",
    "vet", "veterinar", "waterproof", "dishwasher", "silent", "whisper", "quiet",
    "low-noise", "ultra-quiet", "decibel", "stainless steel", "304", "cordless",
    "battery", "rechargeable", "wireless", "universal", "certified", "patent",
    "anxiety", "therapy", "cure", "prevent", "chew-proof", "indestructible",
    "escape-proof", "no-pull", "ul listed", "etl", "fcc",
]

# 警告：AI 味 / 空泛营销词（词表只在这里维护）
STYLE_WARN = [
    "perfect", "perfectly", "ultimate", "premium", "effortless", "effortlessly",
    "seamless", "seamlessly", "elevate", "game-changer", "say goodbye",
    "peace of mind", "worry-free", "revolutionary", "unparalleled",
    "cutting-edge", "state-of-the-art", "must-have", "look no further",
]

EMPTY_LEADS = {"this", "it", "its", "these", "our", "we", "you", "your"}


def norm_tok(s):
    return unicodedata.normalize("NFKC", s).lower().replace("’", "'")


def parse_bold(text):
    """返回 (plain, spans, errors)。text 应已做 NFKC。"""
    parts = text.split("**")
    errs = []
    if len(parts) % 2 == 0:
        errs.append("存在未闭合的 ** 标记")
    plain = ""
    spans = []
    for i, p in enumerate(parts):
        if i % 2 == 1:
            if not p.strip():
                errs.append("存在空加粗")
            elif p != p.strip():
                errs.append("加粗范围含首尾空格（可能嵌套或错位）: %r" % p)
            spans.append((len(plain), len(plain) + len(p)))
        plain += p
    if "*" in plain:
        errs.append("正文残留单个 * 号")
    for s, e in spans:
        if s > 0 and plain[s - 1].isalnum():
            errs.append("加粗断词（前）: %r" % plain[s:e])
        if e < len(plain) and plain[e].isalnum():
            errs.append("加粗断词（后）: %r" % plain[s:e])
    return plain, spans, errs


def tok_spans(plain):
    return [(norm_tok(m.group()), m.start(), m.end()) for m in TOKEN_RE.finditer(plain)]


def find_occurrences(plain, ts, forms):
    """forms: [(tokens_tuple, kidx, form_text)]。要求相邻 token 之间只有空白。"""
    toks = [t[0] for t in ts]
    out = []
    for ptoks, kidx, form in forms:
        n = len(ptoks)
        if n == 0:
            continue
        for i in range(len(toks) - n + 1):
            if tuple(toks[i:i + n]) != ptoks:
                continue
            ok = True
            for k in range(n - 1):
                if plain[ts[i + k][2]:ts[i + k + 1][1]].strip() != "":
                    ok = False
                    break
            if ok:
                out.append((ts[i][1], ts[i + n - 1][2], kidx, form))
    return out


def clen(raw):
    return len(raw.replace("**", "").strip())


def split_paragraphs(desc):
    d = desc.strip()
    if not d:
        return []
    paras = [p for p in re.split(r"\n\s*\n", d) if p.strip()]
    if len(paras) == 1 and "\n" in d:
        paras = [l for l in d.split("\n") if l.strip()]
    return paras


def validate(data, limits=None):
    L = dict(LIMITS)
    L.update(data.get("limits", {}) or {})
    if limits:
        L.update(limits)

    hard, warn = [], []

    brand = data.get("brand", "") or ""
    species = (data.get("species") or "").lower()

    title_raw = data.get("title", "") or ""
    hl_raw = data.get("highlights", "") or ""
    bullets_raw = [re.sub(r"^\s*\d+[.)]\s*", "", b) for b in (data.get("bullets") or [])]
    desc_raw = (data.get("description", "") or "").replace("\r\n", "\n")
    paras = split_paragraphs(desc_raw)

    # 关键词表
    keywords = []
    for k in data.get("keywords", []) or []:
        if isinstance(k, str):
            k = {"phrase": k}
        keywords.append({
            "phrase": k["phrase"],
            "variants": list(k.get("variants", []) or []),
            "core": bool(k.get("core", False)),
        })
    forms = []
    for ki, k in enumerate(keywords):
        for f in [k["phrase"]] + k["variants"]:
            ptoks = tuple(norm_tok(m.group()) for m in TOKEN_RE.finditer(unicodedata.normalize("NFKC", f)))
            forms.append((ptoks, ki, f))

    modules = {
        "title": [title_raw],
        "highlights": [hl_raw],
        "bullets": bullets_raw,
        "description": paras,
    }

    # ---- 字符与结构 ----
    tlen = clen(title_raw)
    hlen = clen(hl_raw)
    blens = [clen(b) for b in bullets_raw]
    btotal = sum(blens)
    dlen = len(desc_raw.replace("**", "").strip())

    if tlen == 0:
        hard.append("标题为空")
    if tlen > L["title_max"]:
        hard.append("标题 %d 字符，超过 %d" % (tlen, L["title_max"]))
    if hlen == 0:
        hard.append("亮点为空")
    if hlen > L["highlights_max"]:
        hard.append("亮点 %d 字符，超过 %d" % (hlen, L["highlights_max"]))
    if len(bullets_raw) != L["bullet_count"]:
        hard.append("五点数量为 %d，应为 %d" % (len(bullets_raw), L["bullet_count"]))
    for i, n in enumerate(blens, 1):
        if n > L["bullet_max"]:
            hard.append("五点第 %d 条 %d 字符，超过 %d" % (i, n, L["bullet_max"]))
    if btotal > L["bullets_total_max"]:
        hard.append("五点合计 %d 字符，超过 %d" % (btotal, L["bullets_total_max"]))
    if dlen == 0:
        hard.append("详情为空")
    if dlen > L["description_max"]:
        hard.append("详情 %d 字符，超过 %d" % (dlen, L["description_max"]))
    if paras and not (L["desc_paragraphs_min"] <= len(paras) <= L["desc_paragraphs_max"]):
        hard.append("详情为 %d 段，应为 %d–%d 段"
                    % (len(paras), L["desc_paragraphs_min"], L["desc_paragraphs_max"]))

    # ---- 标题专项 ----
    title_plain_for_chars = title_raw.replace("**", "")
    check_text = title_plain_for_chars
    if brand:
        check_text = check_text.replace(brand, "")
    bad = sorted({c for c in check_text if c in TITLE_FORBIDDEN})
    if bad:
        hard.append("标题含禁用字符: %s" % " ".join(bad))

    words = [norm_tok(m.group()) for m in TOKEN_RE.finditer(unicodedata.normalize("NFKC", title_plain_for_chars))]
    seen = {}
    for w in words:
        if w in TITLE_STOPWORDS:
            continue
        fold = w[:-1] if len(w) > 3 and w.endswith("s") else w
        seen[fold] = seen.get(fold, 0) + 1
    for w, n in seen.items():
        if n > 2:
            hard.append("标题单词 %r（含单复数折叠）出现 %d 次，超过 2 次" % (w, n))

    # ---- 亮点专项 ----
    if hl_raw and title_raw:
        ht = {w for w in words_of(hl_raw)}
        tt = {w for w in words_of(title_raw)}
        if ht and len(ht & tt) / len(ht) > 0.6:
            warn.append("亮点与标题用词重合超过 60%，疑似复读标题")

    # ---- 五点专项 ----
    prefixes = []
    for i, b in enumerate(bullets_raw, 1):
        plain = b.replace("**", "").strip()
        m = re.match(r"^([^:]{2,80}):\s+(\S.*)$", plain, re.S)
        if not m:
            hard.append("五点第 %d 条不是「卖点短语: 说明」结构" % i)
            continue
        prefix, rest = m.group(1).strip(), m.group(2).strip()
        prefixes.append(prefix.lower())
        if len(prefix.split()) > 8:
            warn.append("五点第 %d 条前缀超过 8 个词，疑似关键词串" % i)
        if prefix.isupper() and len(prefix) > 12:
            warn.append("五点第 %d 条前缀为全大写长标题" % i)
        first = re.match(r"[A-Za-z']+", rest)
        if first and first.group().lower() in EMPTY_LEADS:
            warn.append("五点第 %d 条说明以无信息代词开头: %s" % (i, first.group()))
    if len(prefixes) != len(set(prefixes)):
        warn.append("五点存在重复的卖点前缀")

    # ---- 全文本规则 ----
    all_raw = {"title": title_raw, "highlights": hl_raw,
               "bullets": "\n".join(bullets_raw), "description": desc_raw}
    for mod, raw in all_raw.items():
        txt = unicodedata.normalize("NFKC", raw.replace("**", ""))
        low = txt.lower()
        for pat, msg in HARD_PATTERNS:
            if re.search(pat, low if "A-Z" not in pat else txt):
                hard.append("[%s] %s" % (mod, msg))
        odd = sorted({c for c in raw if unicodedata.category(c) == "So"})
        if odd:
            warn.append("[%s] 含符号/Emoji 字符: %s" % (mod, " ".join(odd)))
        ev = [t for t in EVIDENCE_TERMS if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", low)]
        if ev:
            warn.append("[%s] 需对照产品资料核证（无证据就删）: %s" % (mod, ", ".join(sorted(set(ev)))))
        st = [t for t in STYLE_WARN if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", low)]
        if st:
            warn.append("[%s] 空泛/AI 味用词: %s" % (mod, ", ".join(st)))
        if species in ("dog", "cat"):
            other = r"\b(?:cats?|kittens?|kitty|kitties)\b" if species == "dog" else r"\b(?:dogs?|puppy|puppies|pups?)\b"
            hit = sorted(set(re.findall(other, low)))
            if hit:
                warn.append("[%s] 目标对象为 %s，但出现另一对象用词: %s" % (mod, species, ", ".join(hit)))

    # ---- 关键词：计数、加粗、覆盖 ----
    counts = {}
    present_forms = set()
    unbolded, notmax, notadmitted = [], [], []
    for mod, segs in modules.items():
        for seg in segs:
            nseg = unicodedata.normalize("NFKC", seg)
            plain, spans, errs = parse_bold(nseg)
            for e in errs:
                hard.append("[%s] %s" % (mod, e))
            if not forms:
                continue
            ts = tok_spans(plain)
            occ = find_occurrences(plain, ts, forms)
            for (s, e, ki, form) in occ:
                counts[(mod, ki, form)] = counts.get((mod, ki, form), 0) + 1
                present_forms.add((ki, form))
            if errs:
                continue
            maximal = set()
            for (s, e, ki, form) in occ:
                contained = any(
                    (s2 <= s and e2 >= e and (s2, e2) != (s, e)) for (s2, e2, _, _) in occ)
                if not contained:
                    maximal.add((s, e))
            all_ranges = {(s, e) for (s, e, _, _) in occ}
            for rng in sorted(maximal):
                if rng not in set(spans):
                    unbolded.append("[%s] %s" % (mod, plain[rng[0]:rng[1]]))
            for sp in spans:
                if sp in maximal:
                    continue
                if sp in all_ranges:
                    notmax.append("[%s] %s" % (mod, plain[sp[0]:sp[1]]))
                else:
                    notadmitted.append("[%s] %s" % (mod, plain[sp[0]:sp[1]]))

    if unbolded:
        warn.append("准入词组出现但未加粗: " + "; ".join(unbolded[:12]))
    if notmax:
        warn.append("加粗未按最长匹配: " + "; ".join(notmax[:12]))
    if notadmitted:
        warn.append("加粗内容不在准入词表: " + "; ".join(notadmitted[:12]))

    core_viol = []
    for ki, k in enumerate(keywords):
        if not k["core"]:
            continue
        for form in [k["phrase"]] + k["variants"]:
            for mod in modules:
                n = counts.get((mod, ki, form), 0)
                cap = L["core_cap_title"] if mod == "title" else L["core_cap_other"]
                if n > cap:
                    core_viol.append("核心词 %r 在 %s 出现 %d 次，上限 %d" % (form, mod, n, cap))
    for v in core_viol:
        hard.append(v)

    covered, missing = [], []
    for ki, k in enumerate(keywords):
        if any((ki, f) in present_forms for f in [k["phrase"]] + k["variants"]):
            covered.append(k["phrase"])
        else:
            missing.append(k["phrase"])

    stats = {
        "title_len": tlen, "highlights_len": hlen, "bullet_lens": blens,
        "bullets_total": btotal, "description_len": dlen,
        "description_paragraphs": len(paras),
        "limits": {"title": L["title_max"], "highlights": L["highlights_max"],
                   "bullet": L["bullet_max"], "bullets_total": L["bullets_total_max"],
                   "description": L["description_max"]},
        "keywords_total": len(keywords), "keywords_covered": len(covered),
        "keywords_missing": missing, "core_cap_violations": len(core_viol),
    }
    stats["summary_line"] = summary_line(stats)
    return {"hard_fail": hard, "warnings": warn, "stats": stats}


def words_of(raw):
    return [w for w in (norm_tok(m.group()) for m in TOKEN_RE.finditer(
        unicodedata.normalize("NFKC", raw.replace("**", "")))) if w not in TITLE_STOPWORDS]


def summary_line(s):
    lim = s["limits"]
    b = "/".join(str(n) for n in s["bullet_lens"])
    line = ("字符（去加粗）：标题 %d/%d，亮点 %d/%d，五点 %s（合计 %d/%d），详情 %d/%d"
            % (s["title_len"], lim["title"], s["highlights_len"], lim["highlights"],
               b, s["bullets_total"], lim["bullets_total"],
               s["description_len"], lim["description"]))
    if s["keywords_total"]:
        line += "；目标词覆盖 %d/%d" % (s["keywords_covered"], s["keywords_total"])
        if s["keywords_missing"]:
            line += "（未覆盖：%s）" % ", ".join(s["keywords_missing"])
        line += "；核心词重复违规 %d 项" % s["core_cap_violations"]
    return line


def format_report(rep):
    out = []
    st = rep["stats"]
    out.append("== 硬性失败（%d）==" % len(rep["hard_fail"]))
    out.extend("  ✗ " + m for m in rep["hard_fail"]) if rep["hard_fail"] else out.append("  无")
    out.append("== 警告（%d）==" % len(rep["warnings"]))
    out.extend("  ! " + m for m in rep["warnings"]) if rep["warnings"] else out.append("  无")
    out.append("== 统计 ==")
    out.append("  " + st["summary_line"])
    out.append("  详情段数 %d" % st["description_paragraphs"])
    out.append("结论: " + ("未通过，需修改后复核" if rep["hard_fail"] else "硬约束通过（警告项仍需人工判断）；这不等于亚马逊后台验证通过"))
    return "\n".join(out)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa
        print("读取输入失败: %s" % e)
        return 2
    rep = validate(data)
    if "--json" in argv:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(format_report(rep))
    return 1 if rep["hard_fail"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
