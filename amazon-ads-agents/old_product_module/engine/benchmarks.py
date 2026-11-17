"""行业基准与自有历史基准（V1.5）。

两类数字，按周累积在 GitHub：
- 市场基准【行业基准】：卖家后台「品牌分析 → 搜索查询表现（SQP）」每个搜索词的全市场
  展示 / 点击 / 购买总数 → 市场 CTR、市场 CVR，以及我们品牌的份额。
- 自有历史【自有历史】：categories/<品类>/ops/weekly/*/raw 下累积的 SP 搜索词报表 →
  本品类（按型号）CTR、CVR、CPC、CPA 的周序列和关键词分布。

用途边界（agents/knowledge-base.md）：只用于诊断方向、新词起始竞价参考、阈值复核建议；
不触发否词、暂停、降价、提价，也不自动改 thresholds.md。
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .loaders import LoadedReports, PerfRow, load_reports, norm_text, num
from .xlsx_reader import read_table

WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")

DEFAULTS = {
    "window_weeks": 12,          # 滚动窗口
    "sqp_min_market_clicks": 50,  # 市场点击少于此值的搜索词不计入市场 CVR
    "own_min_weeks": 4,          # 自有历史至少几周才出阈值复核建议
    "own_min_orders": 30,        # 自有历史窗口内至少几单
    "keyword_min_orders": 2,     # 关键词 CPA 分布只取 >= 2 单的词
    "keyword_min_clicks": 20,    # 关键词 CVR / 对比市场只取 >= 20 点击的词
    "diag_ratio_low": 0.70,      # 我们 < 市场 × 70% 标为“低于市场”
    "threshold_review_gap": 0.15,  # 自有分布偏离当前阈值 15% 以上提示复核
    "new_word_top_n": 15,
}


# ---------------- SQP 读取 ----------------

def _n(h: object) -> str:
    return re.sub(r"[\s:：_\-（）()#/]", "", str(h)).lower()


def _find(headers: list[str], group: tuple[str, ...], kind: str) -> str | None:
    """kind = total / brand。排除份额、比率、价格、配送列。"""
    bad = ("share", "份额", "%", "rate", "率", "price", "价格", "价", "shipping", "配送", "score", "分数")
    for h in headers:
        n = _n(h)
        if not any(g in n for g in group) or any(b in n for b in bad):
            continue
        if kind == "total" and ("total" in n or "总" in n):
            return h
        if kind == "brand" and ("brand" in n or "品牌" in n or "asin" in n) and ("count" in n or "数" in n):
            return h
    return None


def read_sqp(path: Path) -> tuple[list[dict], list[str]]:
    rows = read_table(path, header_hints=("searchquery", "搜索查询"))
    if not rows:
        return [], [f"{path.name} 没有数据行"]
    headers = list(rows[0].keys())
    q = next((h for h in headers if _n(h) in ("searchquery", "搜索查询", "搜索查询词")), None)
    vol = next((h for h in headers if _n(h) in ("searchqueryvolume", "搜索查询量")), None)
    cols = {
        "impr": _find(headers, ("impression", "展示", "曝光"), "total"),
        "clicks": _find(headers, ("click", "点击"), "total"),
        "purchases": _find(headers, ("purchase", "购买"), "total"),
        "brand_clicks": _find(headers, ("click", "点击"), "brand"),
        "brand_purchases": _find(headers, ("purchase", "购买"), "brand"),
    }
    need = [k for k in ("impr", "clicks", "purchases") if not cols[k]]
    if not q or need:
        return [], [f"{path.name} 识别不到 SQP 字段 {(['搜索查询'] if not q else []) + need}；表头为 {headers}。请在 engine/benchmarks.py 补充匹配"]
    out = []
    for r in rows:
        term = norm_text(r.get(q))
        if not term:
            continue
        out.append({
            "term": term,
            "volume": num(r.get(vol)) if vol else 0.0,
            **{k: (num(r.get(c)) if c else 0.0) for k, c in cols.items()},
        })
    return out, []


# ---------------- 数据结构 ----------------

@dataclass
class Agg:
    impressions: float = 0
    clicks: float = 0
    spend: float = 0
    orders: float = 0

    def add(self, r: PerfRow) -> None:
        self.impressions += r.impressions
        self.clicks += r.clicks
        self.spend += r.spend
        self.orders += r.orders

    @property
    def ctr(self):
        return self.clicks / self.impressions if self.impressions else None

    @property
    def cvr(self):
        return self.orders / self.clicks if self.clicks else None

    @property
    def cpc(self):
        return self.spend / self.clicks if self.clicks else None

    @property
    def cpa(self):
        return self.spend / self.orders if self.orders else None


@dataclass
class MarketTerm:
    term: str
    volume: float = 0
    impr: float = 0
    clicks: float = 0
    purchases: float = 0
    brand_clicks: float = 0
    brand_purchases: float = 0
    weeks: int = 0

    @property
    def ctr(self):
        return self.clicks / self.impr if self.impr else None

    @property
    def cvr(self):
        return self.purchases / self.clicks if self.clicks else None

    @property
    def brand_cvr(self):
        return self.brand_purchases / self.brand_clicks if self.brand_clicks else None

    @property
    def click_share(self):
        return self.brand_clicks / self.clicks if self.clicks else None


@dataclass
class Benchmarks:
    category: str
    model: str
    cfg: dict
    weeks: list[str] = field(default_factory=list)
    sqp_weeks: list[str] = field(default_factory=list)
    market: dict[str, MarketTerm] = field(default_factory=dict)
    own_weekly: list[tuple[str, Agg]] = field(default_factory=list)
    own_total: Agg = field(default_factory=Agg)
    own_terms: dict[str, Agg] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    brand_terms: list[str] = field(default_factory=list)   # 自有品牌词：品牌搜索转化天然偏高，不计入市场均值

    # ---- 市场汇总 ----
    def market_terms(self, include_brand: bool = False) -> list[MarketTerm]:
        m = self.cfg["sqp_min_market_clicks"]
        return [t for t in self.market.values() if t.clicks >= m
                and (include_brand or not any(b and b in t.term for b in self.brand_terms))]

    def market_overall(self) -> dict:
        ts = self.market_terms()
        if not ts:
            return {}
        impr = sum(t.impr for t in ts)
        clicks = sum(t.clicks for t in ts)
        pur = sum(t.purchases for t in ts)
        cvrs = [t.cvr for t in ts if t.cvr is not None]
        return {
            "terms": len(ts),
            "ctr": clicks / impr if impr else None,
            "cvr": pur / clicks if clicks else None,
            "cvr_median": statistics.median(cvrs) if cvrs else None,
        }

    # ---- 自有分布 ----
    def own_distribution(self) -> dict:
        c = self.cfg
        cpas = sorted(a.cpa for a in self.own_terms.values() if a.orders >= c["keyword_min_orders"] and a.cpa)
        cvrs = sorted(a.cvr for a in self.own_terms.values() if a.clicks >= c["keyword_min_clicks"] and a.cvr is not None)
        return {"cpa": _quantiles(cpas), "cvr": _quantiles(cvrs), "cpa_n": len(cpas), "cvr_n": len(cvrs)}

    def own_sample_ok(self) -> bool:
        return len(self.own_weekly) >= self.cfg["own_min_weeks"] and self.own_total.orders >= self.cfg["own_min_orders"]

    def implied_market_cpa(self) -> float | None:
        mo = self.market_overall()
        if mo.get("cvr") and self.own_total.cpc:
            return self.own_total.cpc / mo["cvr"]
        return None

    # ---- 阈值复核建议（只提示，不改文件）----
    def threshold_reviews(self, th: dict) -> list[str]:
        out: list[str] = []
        gap = self.cfg["threshold_review_gap"]
        if not self.own_sample_ok():
            out.append(f"自有历史样本不足（{len(self.own_weekly)} 周 / {self.own_total.orders:g} 单，需 ≥{self.cfg['own_min_weeks']} 周且 ≥{self.cfg['own_min_orders']} 单），暂不出阈值复核建议。")
            return out
        d = self.own_distribution()
        p50 = d["cpa"].get("p50")
        if p50 and d["cpa_n"] >= 5:
            if p50 < th["cpa"]["good"] * (1 - gap):
                out.append(f"【自有历史】近 {len(self.own_weekly)} 周有单关键词 CPA 中位数 ${p50:.2f}，比 {self.model} CPA 优质线 ${th['cpa']['good']} 低 {1 - p50 / th['cpa']['good']:.0%}：现行 CPA 阈值可能偏松，建议负责人复核是否下调。")
            elif p50 > th["cpa"]["normal_high"] * (1 + gap):
                out.append(f"【自有历史】近 {len(self.own_weekly)} 周有单关键词 CPA 中位数 ${p50:.2f}，比 {self.model} CPA 正常线上限 ${th['cpa']['normal_high']} 高 {p50 / th['cpa']['normal_high'] - 1:.0%}：先按 R-DIAG 查页面、价格、评价；若确认是市场成本上升，再复核是否上调阈值。")
        c50 = d["cvr"].get("p50")
        if c50 is not None and d["cvr_n"] >= 5:
            if c50 > th["cvr"]["good"] * (1 + gap):
                out.append(f"【自有历史】关键词 CVR 中位数 {c50:.1%}，高于 {self.model} CVR 优质线 {th['cvr']['good']:.1%} 超过 {gap:.0%}：CVR 阈值可能偏低，建议复核。")
            elif c50 < th["cvr"]["normal_low"] * (1 - gap):
                out.append(f"【自有历史】关键词 CVR 中位数 {c50:.1%}，低于 {self.model} CVR 正常线 {th['cvr']['normal_low']:.1%} 超过 {gap:.0%}：先查转化问题，不建议直接下调阈值。")
        mo = self.market_overall()
        if mo.get("cvr_median") is not None and mo["terms"] >= 5 and mo["cvr_median"] > th["cvr"]["good"] * (1 + gap):
            out.append(f"【行业基准】SQP 市场 CVR 中位数 {mo['cvr_median']:.1%}（{mo['terms']} 个词），高于 {self.model} CVR 优质线 {th['cvr']['good']:.1%}：品类整体转化高于现行阈值，建议复核。")
        if not out:
            out.append("自有历史与现行阈值偏差在范围内，暂不建议调整。")
        out.append(f"调整流程：负责人审批 → 同时改 `categories/{self.category}/thresholds.md` 和 `engine.json` → 升版本、写“Grok 须知”。引擎不会自动改阈值。")
        return out

    # ---- 当前链接对比市场 ----
    def compare_terms(self, st_rows: list[PerfRow]) -> list[dict]:
        cur: dict[str, Agg] = defaultdict(Agg)
        for r in st_rows:
            if r.search_term:
                cur[r.search_term].add(r)
        out = []
        low = self.cfg["diag_ratio_low"]
        for term, a in cur.items():
            mt = self.market.get(term)
            if not mt or a.clicks < self.cfg["keyword_min_clicks"] or mt.clicks < self.cfg["sqp_min_market_clicks"]:
                continue
            flags = []
            if mt.cvr and a.cvr is not None and a.cvr < mt.cvr * low:
                flags.append("转化低于市场：先查页面、价格、评价、变体，不建议靠提价解决")
            if mt.ctr and a.ctr is not None and a.ctr < mt.ctr * low:
                flags.append("点击率低于市场：查主图、价格、标题、广告位")
            if mt.cvr and a.cvr is not None and a.cvr >= mt.cvr * 1.2:
                flags.append("转化高于市场：有放量基础（放量仍按引擎和成熟度）")
            out.append({"term": term, "own": a, "market": mt, "flags": flags})
        return sorted(out, key=lambda x: -x["own"].clicks)

    def new_word_refs(self, target_cpa: float, targeted: set[str], excluded: list[str]) -> list[dict]:
        out = []
        for t in sorted(self.market_terms(), key=lambda t: -(t.volume or t.clicks)):
            if t.term in targeted or any(x and x in t.term for x in excluded) or not t.cvr:
                continue
            out.append({"term": t.term, "market": t, "bid_ref": round(target_cpa * t.cvr, 2)})
            if len(out) >= self.cfg["new_word_top_n"]:
                break
        return out

    def to_json(self) -> dict:
        mo = self.market_overall()
        return {
            "category": self.category, "model": self.model,
            "weeks": self.weeks, "sqp_weeks": self.sqp_weeks,
            "market_overall": mo,
            "own_total": _agg_json(self.own_total),
            "own_weekly": [{"week": w, **_agg_json(a)} for w, a in self.own_weekly],
            "own_distribution": self.own_distribution(),
            "implied_market_cpa": self.implied_market_cpa(),
            "market_terms": [{"term": t.term, "volume": t.volume, "ctr": t.ctr, "cvr": t.cvr, "click_share": t.click_share,
                              "brand_cvr": t.brand_cvr, "weeks": t.weeks} for t in sorted(self.market_terms(include_brand=True), key=lambda t: -t.clicks)],
            "config": self.cfg,
        }


def _agg_json(a: Agg) -> dict:
    return {"impressions": a.impressions, "clicks": a.clicks, "spend": round(a.spend, 2), "orders": a.orders,
            "ctr": a.ctr, "cvr": a.cvr, "cpc": a.cpc, "cpa": a.cpa}


def _quantiles(xs: list[float]) -> dict:
    if not xs:
        return {}
    if len(xs) == 1:
        return {"p25": xs[0], "p50": xs[0], "p75": xs[0]}
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return {"p25": q[0], "p50": q[1], "p75": q[2]}


def _model_match(model: str, *names: str) -> bool:
    pat = re.compile(rf"(?<![0-9a-z]){re.escape(model.lower())}(?![a-z])")
    return any(pat.search(str(n).lower()) for n in names)


# ---------------- 构建 ----------------

def build(category: str, ops_dir: Path, model: str, cfg: dict | None = None, up_to_week: str | None = None,
          brand_terms: list[str] | None = None) -> Benchmarks:
    c = {k: v for k, v in {**DEFAULTS, **(cfg or {})}.items() if not k.startswith("_")}
    bm = Benchmarks(category=category, model=model, cfg=c, brand_terms=[norm_text(b) for b in (brand_terms or []) if str(b).strip()])
    weekly = ops_dir / "weekly"
    weeks = sorted(p.name for p in weekly.iterdir() if p.is_dir() and WEEK_RE.match(p.name)) if weekly.exists() else []
    if up_to_week:
        weeks = [w for w in weeks if w <= up_to_week]
    weeks = weeks[-c["window_weeks"]:]
    bm.weeks = weeks
    for w in weeks:
        raw = weekly / w / "raw"
        if not raw.exists():
            continue
        rep: LoadedReports = load_reports(raw)
        # 市场：SQP
        seen_week = False
        for name in rep.market_files:
            rows, warns = read_sqp(raw / name)
            bm.warnings.extend(f"{w}：{x}" for x in warns)
            for r in rows:
                t = bm.market.setdefault(r["term"], MarketTerm(r["term"]))
                t.volume += r["volume"]
                t.impr += r["impr"]
                t.clicks += r["clicks"]
                t.purchases += r["purchases"]
                t.brand_clicks += r["brand_clicks"]
                t.brand_purchases += r["brand_purchases"]
                t.weeks += 1
            seen_week = seen_week or bool(rows)
        if seen_week:
            bm.sqp_weeks.append(w)
        # 自有：SP 搜索词（按型号过滤：活动或广告组名称含型号）
        st = rep.perf.get("st_summary") or rep.perf.get("st_daily") or []
        rows = [r for r in st if _model_match(model, r.campaign, r.ad_group)]
        if st and not rows:
            bm.warnings.append(f"{w}：搜索词报表里没有活动 / 广告组名称含 {model} 的行，按命名规则无法区分型号，该周自有数据未计入")
        if not rows:
            continue
        a = Agg()
        for r in rows:
            a.add(r)
            bm.own_total.add(r)
            bm.own_terms.setdefault(r.search_term, Agg()).add(r)
        bm.own_weekly.append((w, a))
    return bm


# ---------------- 输出 ----------------

def _p(v, money=False):
    if v is None:
        return "—"
    return f"${v:.2f}" if money else f"{v:.1%}"


def render_section(bm: Benchmarks, th: dict, target_cpa: float, st_rows: list[PerfRow], targeted: set[str], excluded: list[str]) -> list[str]:
    """方案报告里的“对比行业与自有历史”一节。"""
    L = ["## 对比行业与自有历史（参考，不触发动作）\n"]
    L.append("> 【行业基准】来自卖家后台品牌分析 SQP（全市场，含自然流量和广告；市场均值不含自有品牌词）；【自有历史】来自 `ops/weekly/` 累积的 SP 搜索词报表。"
             "这里的数字只用于判断问题方向、新词起始竞价参考和阈值复核，**不会生成否词、暂停、调价动作**（`agents/knowledge-base.md` 第二节）。\n")
    mo = bm.market_overall()
    d = bm.own_distribution()
    L.append(f"- 窗口：最近 {len(bm.weeks)} 周（{bm.weeks[0] + ' ~ ' + bm.weeks[-1] if bm.weeks else '无累积数据'}）；含 SQP 的周 {len(bm.sqp_weeks)} 周；型号 {bm.model} 自有数据 {len(bm.own_weekly)} 周")
    L.append("")
    L.append("| 指标 | 【行业基准】市场 | 【自有历史】本型号 | 【品类阈值】现行 |")
    L.append("|---|---|---|---|")
    L.append(f"| CTR | {_p(mo.get('ctr'))} | {_p(bm.own_total.ctr)} | 未设 |")
    L.append(f"| CVR | {_p(mo.get('cvr'))}（中位数 {_p(mo.get('cvr_median'))}） | {_p(bm.own_total.cvr)}（关键词中位数 {_p(d['cvr'].get('p50'))}） | 优质 {th['cvr']['good']:.1%} / 正常 {th['cvr']['normal_low']:.1%} |")
    L.append(f"| CPC | — | {_p(bm.own_total.cpc, True)} | — |")
    L.append(f"| CPA | 推算 {_p(bm.implied_market_cpa(), True)}（自有 CPC ÷ 市场 CVR） | {_p(bm.own_total.cpa, True)}（关键词 P25/P50/P75 {_p(d['cpa'].get('p25'), True)} / {_p(d['cpa'].get('p50'), True)} / {_p(d['cpa'].get('p75'), True)}） | 优质 ${th['cpa']['good']} / 正常上限 ${th['cpa']['normal_high']} |")
    L.append("")
    if not bm.market:
        L.append("- 【缺失数据】还没有 SQP 数据：请 Grok 按 `agents/grok-operator.md` A1 每周导出「搜索查询表现」。\n")

    L.append("### 阈值复核建议\n")
    L.extend(f"- {s}" for s in bm.threshold_reviews(th))
    L.append("")

    comp = bm.compare_terms(st_rows)
    L.append("### 本周搜索词对比市场\n")
    if comp:
        L.append("| 搜索词 | 我们（广告） | 市场 | 我们品牌点击份额 | 判断 |")
        L.append("|---|---|---|---|---|")
        for x in comp[:30]:
            o, m = x["own"], x["market"]
            L.append(f"| {x['term']} | 点击{o.clicks:.0f} CTR {_p(o.ctr)} CVR {_p(o.cvr)} | CTR {_p(m.ctr)} CVR {_p(m.cvr)} | {_p(m.click_share)} | {'；'.join(x['flags']) or '与市场接近'} |")
    else:
        L.append(f"无（需要搜索词同时在 SQP 中、我们点击 ≥{bm.cfg['keyword_min_clicks']}、市场点击 ≥{bm.cfg['sqp_min_market_clicks']}）。")
    L.append("")

    refs = bm.new_word_refs(target_cpa, targeted, excluded)
    L.append("### 未投放的市场词：起始竞价参考\n")
    if refs:
        L.append(f"起始竞价参考 = 目标 CPA ${target_cpa:g} × 市场 CVR。只作新建广告时的参考，加词仍按引擎和成熟度，需用户审批。\n")
        L.append("| 搜索词 | 市场搜索量 | 市场 CVR | 起始竞价参考 |")
        L.append("|---|---|---|---|")
        for r in refs:
            L.append(f"| {r['term']} | {r['market'].volume:,.0f} | {_p(r['market'].cvr)} | ${r['bid_ref']:.2f} |")
    else:
        L.append("无。")
    L.append("")
    if bm.warnings:
        L.extend(f"- ⚠️ {w}" for w in bm.warnings)
        L.append("")
    return L


def render_file(bm: Benchmarks, th: dict) -> str:
    """categories/<品类>/benchmarks/基准线_<型号>.md：每周刷新的品类基准线。"""
    mo = bm.market_overall()
    d = bm.own_distribution()
    L = [f"# {bm.category} {bm.model} 基准线（自动生成，勿手改）\n",
         f"窗口：最近 {len(bm.weeks)} 周（{bm.weeks[0] + ' ~ ' + bm.weeks[-1] if bm.weeks else '无'}）；SQP 周数 {len(bm.sqp_weeks)}；自有数据周数 {len(bm.own_weekly)}。\n",
         "## 汇总\n",
         "| 指标 | 【行业基准】市场 | 【自有历史】 | 【品类阈值】现行 |", "|---|---|---|---|",
         f"| CTR | {_p(mo.get('ctr'))} | {_p(bm.own_total.ctr)} | 未设 |",
         f"| CVR | {_p(mo.get('cvr'))}（中位数 {_p(mo.get('cvr_median'))}，{mo.get('terms', 0)} 个词） | {_p(bm.own_total.cvr)}（关键词 P25/P50/P75 {_p(d['cvr'].get('p25'))} / {_p(d['cvr'].get('p50'))} / {_p(d['cvr'].get('p75'))}，{d['cvr_n']} 个词） | 优质 {th['cvr']['good']:.1%} / 正常 {th['cvr']['normal_low']:.1%} / 高风险 {th['cvr']['high_risk']:.1%} |",
         f"| CPC | — | {_p(bm.own_total.cpc, True)} | — |",
         f"| CPA | 推算 {_p(bm.implied_market_cpa(), True)} | {_p(bm.own_total.cpa, True)}（关键词 P25/P50/P75 {_p(d['cpa'].get('p25'), True)} / {_p(d['cpa'].get('p50'), True)} / {_p(d['cpa'].get('p75'), True)}，{d['cpa_n']} 个词） | 优质 ${th['cpa']['good']} / 正常上限 ${th['cpa']['normal_high']} / 高风险 ${th['cpa']['high_risk']} |",
         "", "## 阈值复核建议\n"]
    L.extend(f"- {s}" for s in bm.threshold_reviews(th))
    L += ["", "## 自有周序列\n", "| 周 | 点击 | 花费 | 订单 | CTR | CVR | CPC | CPA |", "|---|---|---|---|---|---|---|---|"]
    for w, a in bm.own_weekly:
        L.append(f"| {w} | {a.clicks:.0f} | ${a.spend:.2f} | {a.orders:g} | {_p(a.ctr)} | {_p(a.cvr)} | {_p(a.cpc, True)} | {_p(a.cpa, True)} |")
    L += ["", "## 市场词（SQP，按市场点击排序，前 50）\n", "| 搜索词 | 搜索量 | 市场 CTR | 市场 CVR | 我们点击份额 | 我们品牌 CVR | 周数 |", "|---|---|---|---|---|---|---|"]
    for t in sorted(bm.market_terms(include_brand=True), key=lambda t: -t.clicks)[:50]:
        L.append(f"| {t.term} | {t.volume:,.0f} | {_p(t.ctr)} | {_p(t.cvr)} | {_p(t.click_share)} | {_p(t.brand_cvr)} | {t.weeks} |")
    if bm.warnings:
        L += ["", "## 警告\n"] + [f"- {w}" for w in bm.warnings]
    return "\n".join(L) + "\n"


def write_outputs(bm: Benchmarks, th: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"基准线_{bm.model}.md"
    js = out_dir / f"latest_{bm.model}.json"
    md.write_text(render_file(bm, th), encoding="utf-8")
    js.write_text(json.dumps(bm.to_json(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return [md, js]
