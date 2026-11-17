"""Classify report files, map column names (Amazon English / 领星中文) and normalise rows."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from .xlsx_reader import read_table

# 标准报表名 -> 内部 key（与 agents/old-product-promotion.md 一致）
REPORT_NAMES = {
    "st_daily": "SP搜索词-按词-每日明细",
    "st_summary": "SP搜索词-按词-汇总",
    "targeting": "SP投放对象 / 关键词 / 商品投放报告",
    "placement": "SP广告位报告",
    "advertised": "SP广告商品报告",
    "settings": "Campaign / Ad Group 设置表",
}

MISSING_IMPACT = {
    "st_daily": "无法判断近 3 天趋势和是否可放大；否词改用汇总表判断",
    "st_summary": "可用每日明细汇总代替，但稳定性下降",
    "targeting": "无法给出投放对象级别的竞价动作",
    "placement": "无法判断广告位溢价是否合理",
    "advertised": "无法判断变体和广告商品层面的优化动作（本版引擎暂未实现该诊断）",
    "settings": "没有当前竞价、预算、溢价，只能判断方向，不能生成可执行指令",
}


def classify_file(name: str) -> str | None:
    n = name.lower().replace(" ", "")
    if "搜索词" in n or "searchterm" in n:
        if "每日" in n or "daily" in n:
            return "st_daily"
        return "st_summary"
    if "投放对象" in n or "targeting" in n or "关键词报告" in n:
        return "targeting"
    if "广告位" in n or "placement" in n:
        return "placement"
    if "广告商品" in n or "advertisedproduct" in n:
        return "advertised"
    if "设置" in n or "bulk" in n or "批量" in n:
        return "settings"
    return None


def _norm(h: str) -> str:
    return re.sub(r"[\s_\-（）()#]", "", str(h)).lower()


ALIASES: dict[str, list[str]] = {
    "date": ["date", "日期", "startdate", "开始日期"],
    "campaign": ["campaignname", "campaign", "广告活动", "广告活动名称", "campaignname(informationalonly)", "campaignnameinformationalonly"],
    "ad_group": ["adgroupname", "adgroup", "广告组", "广告组名称", "adgroupnameinformationalonly"],
    "targeting": ["targeting", "keywordtext", "keyword", "投放", "关键词", "投放词", "投放对象", "keywordortargeting", "producttargetingexpression", "投放表达式"],
    "match_type": ["matchtype", "匹配类型", "匹配方式"],
    "search_term": ["customersearchterm", "searchterm", "用户搜索词", "客户搜索词", "买家搜索词", "搜索词"],
    "impressions": ["impressions", "曝光量", "展示量", "曝光", "展示次数"],
    "clicks": ["clicks", "点击", "点击量", "点击次数"],
    "spend": ["spend", "cost", "花费", "广告花费", "支出"],
    "orders": ["7daytotalorders", "14daytotalorders", "orders", "广告订单", "广告订单量", "订单量", "订单", "7天总订单数", "广告订单数"],
    "sales": ["7daytotalsales", "14daytotalsales", "sales", "广告销售额", "销售额", "7天总销售额"],
    "placement": ["placement", "广告位", "展示位置", "placementtype", "位置"],
    "bid": ["bid", "竞价", "keywordbid", "当前竞价", "maxbid"],
    "ad_group_default_bid": ["adgroupdefaultbid", "默认竞价", "广告组默认竞价"],
    "budget": ["dailybudget", "budget", "预算", "每日预算", "日预算"],
    "percentage": ["percentage", "百分比", "溢价", "竞价调整", "溢价比例"],
    "entity": ["entity", "实体", "记录类型", "实体类型"],
    "state": ["state", "状态", "campaignstate", "运行状态"],
    "tos_pct": ["topofsearch%", "topofsearch", "tos溢价", "搜索结果顶部", "搜索结果顶部溢价", "topofsearchfirstpage"],
    "ros_pct": ["restofsearch%", "restofsearch", "ros溢价", "搜索结果其余位置", "其余位置溢价"],
    "pp_pct": ["productpage%", "productpage", "pp溢价", "商品页面", "商品页面溢价"],
}


def map_columns(headers: list[str]) -> dict[str, str]:
    normed = {_norm(h): h for h in headers}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for field_name, aliases in ALIASES.items():
        for a in aliases:
            a_n = _norm(a)
            if a_n in normed and normed[a_n] not in used:
                mapping[field_name] = normed[a_n]
                used.add(normed[a_n])
                break
    # 宽松匹配：Amazon 的 "7 Day Total Orders (#)" 等
    for field_name, needle in (("orders", "orders"), ("sales", "sales"), ("spend", "spend")):
        if field_name not in mapping:
            for n, h in normed.items():
                if needle in n and h not in used and not any(x in n for x in ("units", "acos", "cost", "rate", "per", "roas", "%")):
                    mapping[field_name] = h
                    used.add(h)
                    break
    return mapping


def num(v: object) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "").replace("US", "").replace("￥", "")
    if s in ("", "-", "--", "N/A", "nan"):
        return 0.0
    pct = s.endswith("%")
    s = s.rstrip("%")
    try:
        f = float(s)
    except ValueError:
        return 0.0
    return f / 100 if pct else f


def opt_num(v: object) -> float | None:
    if v is None or str(v).strip() in ("", "-", "--"):
        return None
    return num(v)


def parse_date(v: object) -> dt.date | None:
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):  # Excel serial
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y%m%d", "%b %d, %Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s[:12].strip(), fmt).date()
        except ValueError:
            continue
    return None


def norm_text(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def norm_match(s: object) -> str:
    t = norm_text(s)
    if t in ("exact", "精准", "精确", "negativeexact"):
        return "精准"
    if t in ("phrase", "词组", "短语"):
        return "词组"
    if t in ("broad", "广泛"):
        return "广泛"
    if t in ("", "-", "--", "auto", "自动", "targeting_expression_predefined"):
        return "自动"
    return "商品投放" if ("asin" in t or "category" in t or "类目" in t or "商品" in t or "expression" in t) else t


def norm_placement(s: object) -> str:
    t = norm_text(s)
    if "top" in t or "顶部" in t:
        return "TOS"
    if "detail" in t or "product page" in t or "商品页" in t or "pp" == t:
        return "PP"
    if "rest" in t or "other" in t or "其余" in t or "其他" in t:
        return "ROS"
    return t or "未知"


@dataclass
class PerfRow:
    date: dt.date | None
    campaign: str
    ad_group: str
    targeting: str
    match_type: str
    search_term: str
    placement: str
    impressions: float
    clicks: float
    spend: float
    orders: float
    sales: float


@dataclass
class Settings:
    budgets: dict[str, float] = field(default_factory=dict)            # campaign -> daily budget
    bids: dict[tuple[str, str, str, str], float] = field(default_factory=dict)  # (camp, ag, target, match)
    ag_default_bids: dict[tuple[str, str], float] = field(default_factory=dict)
    placement_pct: dict[tuple[str, str], float] = field(default_factory=dict)  # (camp, TOS/ROS/PP) -> %
    keywords: set[str] = field(default_factory=set)                    # all targeted keyword texts


@dataclass
class LoadedReports:
    perf: dict[str, list[PerfRow]] = field(default_factory=dict)
    settings: Settings | None = None
    files: dict[str, str] = field(default_factory=dict)
    unclassified: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _perf_rows(rows: list[dict], mapping: dict[str, str]) -> list[PerfRow]:
    g = lambda r, k: r.get(mapping[k], "") if k in mapping else ""  # noqa: E731
    out = []
    for r in rows:
        out.append(PerfRow(
            date=parse_date(g(r, "date")),
            campaign=str(g(r, "campaign")).strip(),
            ad_group=str(g(r, "ad_group")).strip(),
            targeting=str(g(r, "targeting")).strip(),
            match_type=norm_match(g(r, "match_type")),
            search_term=norm_text(g(r, "search_term")),
            placement=norm_placement(g(r, "placement")),
            impressions=num(g(r, "impressions")),
            clicks=num(g(r, "clicks")),
            spend=num(g(r, "spend")),
            orders=num(g(r, "orders")),
            sales=num(g(r, "sales")),
        ))
    return out


def _settings(rows: list[dict], mapping: dict[str, str]) -> Settings:
    s = Settings()
    g = lambda r, k: r.get(mapping[k], "") if k in mapping else ""  # noqa: E731
    for r in rows:
        camp = str(g(r, "campaign")).strip()
        ag = str(g(r, "ad_group")).strip()
        target = str(g(r, "targeting")).strip()
        entity = norm_text(g(r, "entity"))
        budget = opt_num(g(r, "budget"))
        bid = opt_num(g(r, "bid"))
        ag_bid = opt_num(g(r, "ad_group_default_bid"))
        if camp and budget is not None and (not entity or entity in ("campaign", "广告活动")):
            s.budgets.setdefault(camp, budget)
        if entity in ("bidding adjustment", "竞价调整", "广告位调整") and "placement" in mapping:
            pct = opt_num(g(r, "percentage"))
            if pct is not None:
                s.placement_pct[(camp, norm_placement(g(r, "placement")))] = pct if pct > 1 else pct * 100
        for key, pl in (("tos_pct", "TOS"), ("ros_pct", "ROS"), ("pp_pct", "PP")):
            v = opt_num(g(r, key))
            if camp and v is not None:
                s.placement_pct.setdefault((camp, pl), v if v > 1 else v * 100)
        if ag_bid is not None and camp and ag:
            s.ag_default_bids.setdefault((camp, ag), ag_bid)
        if entity in ("ad group", "广告组") and bid is not None:
            s.ag_default_bids.setdefault((camp, ag), bid)
            continue
        if target and bid is not None:
            s.bids[(camp, ag, norm_text(target), norm_match(g(r, "match_type")))] = bid
        if target and norm_match(g(r, "match_type")) in ("精准", "词组", "广泛"):
            s.keywords.add(norm_text(target))
    return s


def load_reports(report_dir: Path) -> LoadedReports:
    out = LoadedReports()
    for path in sorted(report_dir.iterdir()):
        if path.is_dir() or path.name.startswith((".", "~")):
            continue
        if path.suffix.lower() not in (".xlsx", ".xlsm", ".csv", ".tsv"):
            continue
        kind = classify_file(path.name)
        if kind is None:
            out.unclassified.append(path.name)
            continue
        if kind in out.files:
            out.warnings.append(f"{REPORT_NAMES[kind]} 有多个文件，只使用 {out.files[kind]}，忽略 {path.name}")
            continue
        rows = read_table(path)
        if not rows:
            out.warnings.append(f"{path.name} 没有数据行")
            continue
        mapping = map_columns(list(rows[0].keys()))
        out.files[kind] = path.name
        if kind == "settings":
            out.settings = _settings(rows, mapping)
            continue
        need = {"campaign", "clicks", "spend", "orders"}
        if kind in ("st_daily", "st_summary"):
            need |= {"search_term"}
        if kind == "placement":
            need |= {"placement"}
        if kind == "targeting":
            need |= {"targeting"}
        if kind == "st_daily":
            need |= {"date"}
        missing = need - set(mapping)
        if missing:
            out.warnings.append(
                f"{path.name} 识别不到字段 {sorted(missing)}；表头为 {list(rows[0].keys())}。请在 engine/loaders.py 的 ALIASES 中补充别名"
            )
            del out.files[kind]
            continue
        out.perf[kind] = _perf_rows(rows, mapping)
    return out
