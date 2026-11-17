"""喂水器老品规则引擎：把 agents/old-product-promotion.md 与 search-term-reinvestment.md
里能量化的规则写成确定性代码。数字全部由这里算，大模型只负责解释和补充判断。"""
from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from dataclasses import dataclass, field

from .loaders import LoadedReports, PerfRow, Settings, norm_text

ASIN_RE = re.compile(r"^b0[a-z0-9]{8}$")


@dataclass
class Metrics:
    impressions: float = 0
    clicks: float = 0
    spend: float = 0
    orders: float = 0
    sales: float = 0

    def add(self, r: PerfRow) -> None:
        self.impressions += r.impressions
        self.clicks += r.clicks
        self.spend += r.spend
        self.orders += r.orders
        self.sales += r.sales

    @property
    def cpa(self) -> float | None:
        return self.spend / self.orders if self.orders else None

    @property
    def acos(self) -> float | None:
        return self.spend / self.sales if self.sales else None

    @property
    def cvr(self) -> float | None:
        return self.orders / self.clicks if self.clicks else None

    def brief(self) -> str:
        parts = [f"点击{self.clicks:.0f}", f"花费${self.spend:.2f}", f"订单{self.orders:g}"]
        if self.cpa is not None:
            parts.append(f"CPA ${self.cpa:.2f}")
        if self.acos is not None:
            parts.append(f"ACOS {self.acos:.0%}")
        if self.cvr is not None:
            parts.append(f"CVR {self.cvr:.1%}")
        return "，".join(parts)


@dataclass
class Action:
    layer: str            # 搜索词 / 投放对象 / 广告位 / 广告活动 / 新增
    campaign: str
    ad_group: str
    target: str
    match_type: str
    action: str           # 加否定-精准 / 加否定-商品 / 降竞价 / 提竞价 / 降广告位溢价 / 提广告位溢价 / 加预算 / 加关键词 / 暂停 / 观察 / 保持
    current: str
    new: str
    reason: str
    metrics: str
    needs_confirm: bool = False
    executable: bool = True
    blocked_by: str = ""  # 成熟度未解锁 / 缺当前值 等


@dataclass
class EngineResult:
    actions: list[Action] = field(default_factory=list)
    campaign_summary: list[dict] = field(default_factory=list)
    totals: Metrics = field(default_factory=Metrics)
    window_note: str = ""
    notes: list[str] = field(default_factory=list)
    last_date: dt.date | None = None


# ---------- 阈值判断 ----------

def level_cpa(v: float | None, th: dict) -> str:
    if v is None:
        return "无订单"
    if v <= th["good"]:
        return "优质"
    if v <= th["normal_high"]:
        return "正常"
    if v < th["high_risk"]:
        return "警戒"
    return "高风险"


def level_acos(v: float | None, th: dict) -> str:
    return level_cpa(v, th)  # 同方向：越低越好


def level_cvr(v: float | None, th: dict) -> str:
    if v is None:
        return "无点击"
    if v >= th["good"]:
        return "优质"
    if v >= th["normal_low"]:
        return "正常"
    if v > th["high_risk"]:
        return "警戒"
    return "高风险"


def no_order_level(m: Metrics, th: dict) -> str | None:
    """点击<2单 / 花费<2单 停止线。"""
    if m.orders >= 2:
        return None
    c, s = th["clicks_no_order"], th["spend_no_order"]
    if m.clicks >= c["high_risk"] or m.spend >= s["high_risk"]:
        return "高风险"
    if m.clicks >= c["warn"] or m.spend >= s["warn"]:
        return "警戒"
    return None


# ---------- 主流程 ----------

class FountainEngine:
    def __init__(self, cfg: dict, profile: dict, maturity: str):
        model = str(profile.get("model", "")).upper()
        if model not in cfg["models"]:
            raise ValueError(f"profile.model 必须是 {list(cfg['models'])} 之一，当前为 {profile.get('model')!r}")
        self.cfg = cfg
        self.th = cfg["models"][model]
        self.model = model
        self.profile = profile
        self.maturity = maturity
        self.unlocked = set(cfg["maturity_unlocks"].get(maturity, []))
        # 竞价调整上限：填数字=人工固定；不填或 "auto"=按历史数据自动（用户 2026-11-17 决定）
        cap = profile.get("bid_cap_pct")
        if isinstance(cap, (int, float)):
            self.cap, self.cap_src = float(cap), "人工设定"
        else:
            self.cap, self.cap_src = float(cfg.get("auto_bid_cap_default", 0.20)), "自动：默认值，待 change-history 满 30 条 14 天效果后按实际效果校准"
        self.cap_confirmed = True  # 自动模式是用户确认的策略，不再逐条二次确认
        self.floor = float(profile.get("bid_floor") or 0.20)
        # 目标 CPA：填数字=人工固定；不填或 "auto"=运行时按链接历史 CPA 推导（见 _resolve_target）
        tc = profile.get("target_cpa")
        self.target_cpa = float(tc) if isinstance(tc, (int, float)) and tc > 0 else None
        self.target_cpa_src = "人工目标CPA" if self.target_cpa else ""
        terms = list(cfg.get("brand_terms", [])) + list(profile.get("brand_terms", [])) + list(profile.get("protected_terms", []))
        self.protected = [norm_text(t) for t in terms if str(t).strip()]
        # 竞品品牌词：知识库 docs/07 —— 可投放但默认不进手动词表，不自动否定、不自动加词
        comp = list(cfg.get("competitor_brand_terms", [])) + list(profile.get("competitor_brand_terms", []))
        self.competitors = [norm_text(t) for t in comp if str(t).strip()]

    def _resolve_target(self, totals: "Metrics") -> None:
        """自动目标 CPA = 链接自身历史 CPA，限定在品类优质线 ~ 正常线上限之间：
        表现好于优质线时不逼着继续压价，差于正常线上限时按品类标准往回拉。"""
        if self.target_cpa:
            return
        th = self.th["cpa"]
        min_orders = int(self.cfg.get("auto_target_min_orders", 10))
        if totals.orders >= min_orders and totals.cpa:
            t = min(max(totals.cpa, th["good"]), th["normal_high"])
            self.target_cpa = round(t, 2)
            self.target_cpa_src = (f"自动：链接历史CPA ${totals.cpa:.2f}（{totals.orders:g}单），"
                                   f"限定在{self.model}品类优质线${th['good']}~正常线上限${th['normal_high']}")
        else:
            self.target_cpa = th["normal_high"]
            self.target_cpa_src = f"自动：历史订单 {totals.orders:g} < {min_orders} 单，暂用{self.model}品类CPA正常线上限"

    # 统一出口：成熟度门控 + 二次确认
    def _emit(self, res: EngineResult, a: Action) -> None:
        if a.action in ("观察", "保持"):
            a.executable = False
        elif a.layer == "广告位" and self.cfg.get("placement_manual_review", True):
            a.executable = False
            a.blocked_by = "【知识库-口径】广告位好坏指标和调价最低数据量待补充（总纲第十四章第17、18条），只做人工复核"
        elif a.action not in self.unlocked:
            a.executable = False
            a.blocked_by = f"成熟度 {self.maturity} 未解锁该动作"
        elif a.current in ("", "待补"):
            a.executable = False
            a.blocked_by = "缺少当前值（需 Campaign / Ad Group 设置表）"
        if a.action in ("加预算", "暂停", "加关键词") or (a.action in ("提竞价", "降竞价") and not self.cap_confirmed):
            a.needs_confirm = True
        res.actions.append(a)

    def run(self, rep: LoadedReports) -> EngineResult:
        res = EngineResult()
        st_rows = rep.perf.get("st_daily") or rep.perf.get("st_summary") or []
        settings = rep.settings or Settings()

        dates = sorted({r.date for r in st_rows if r.date} | {r.date for r in rep.perf.get("targeting", []) if r.date})
        self.last_date = res.last_date = dates[-1] if dates else None
        if dates:
            res.window_note = f"数据周期 {dates[0]} 至 {dates[-1]}（{(dates[-1] - dates[0]).days + 1} 天）；竞价判断用最近 14 天，趋势用 3 天 vs 7 天"
        else:
            res.window_note = "报表无日期字段：按整表周期判断，不能做趋势和放量判断"

        # 整体与活动层
        camp_m: dict[str, Metrics] = defaultdict(Metrics)
        base_rows = rep.perf.get("targeting") or st_rows or rep.perf.get("placement", [])
        for r in base_rows:
            res.totals.add(r)
            camp_m[r.campaign].add(r)
        for camp, m in sorted(camp_m.items(), key=lambda x: -x[1].spend):
            res.campaign_summary.append({
                "campaign": camp, "metrics": m, "cpa_level": level_cpa(m.cpa, self.th["cpa"]) if m.orders >= 2 else "样本不足",
                "acos_level": level_acos(m.acos, self.th["acos"]) if m.orders >= 2 else "样本不足",
                "budget": settings.budgets.get(camp),
            })

        self._resolve_target(res.totals)
        self._search_terms(res, st_rows, settings)
        self._targets(res, rep.perf.get("targeting", []), settings, st_rows)
        self._placements(res, rep.perf.get("placement", []), camp_m, settings)
        self._budgets(res, camp_m, settings, dates)
        self._harvest(res, st_rows, settings, res.totals)
        self._check_bid_ladder(res, settings)
        return res

    # ---- 竞价层级检查：知识库 docs/05 精准 > 词组 > 广泛 > 自动 ----
    RANK = {"精准": 3, "词组": 2, "广泛": 1}

    def _check_bid_ladder(self, res: EngineResult, settings: Settings) -> None:
        def money(s: str) -> float | None:
            try:
                return float(s.replace("$", "")) if s.startswith("$") else None
            except ValueError:
                return None

        # 同一关键词文本，各匹配方式的最终竞价（有调整动作时取新值）
        final: dict[str, dict[str, float]] = defaultdict(dict)
        for (camp, ag, text, mt), bid in settings.bids.items():
            if mt in self.RANK:
                final[text][mt] = max(final[text].get(mt, 0), bid)
        changes = [a for a in res.actions if a.action in ("提竞价", "降竞价") and a.match_type in self.RANK]
        for a in changes:
            v = money(a.new)
            if v is not None and a.executable:
                final[norm_text(a.target)][a.match_type] = v
        for a in changes:
            if a.action != "提竞价" or not a.executable:
                continue
            v = money(a.new)
            for mt, b in final[norm_text(a.target)].items():
                if self.RANK[mt] > self.RANK[a.match_type] and v is not None and v > b:
                    a.executable = False
                    a.blocked_by = f"【知识库-总纲】docs/05 竞价层级：提价后 ${v:.2f} 会高于同词{mt}竞价 ${b:.2f}"
                    break
        for text, bids in final.items():
            order = sorted(bids.items(), key=lambda x: -self.RANK[x[0]])
            for (hi_mt, hi_b), (lo_mt, lo_b) in zip(order, order[1:]):
                if lo_b > hi_b:
                    res.notes.append(f"【知识库-总纲】竞价层级倒挂：「{text}」{lo_mt} ${lo_b:.2f} 高于 {hi_mt} ${hi_b:.2f}，建议人工复核（docs/05 精准>词组>广泛>自动）")

    # ---- 1. 搜索词否定 ----
    def _search_terms(self, res: EngineResult, rows: list[PerfRow], settings: Settings) -> None:
        agg: dict[tuple, Metrics] = defaultdict(Metrics)
        targets_in_group: dict[tuple, set] = defaultdict(set)
        for r in rows:
            agg[(r.campaign, r.ad_group, r.search_term)].add(r)
            if r.match_type == "精准":
                targets_in_group[(r.campaign, r.ad_group)].add(norm_text(r.targeting))
        min_clicks = self.cfg["search_term_negative"]["min_clicks_no_order"]
        spend_hr = self.th["spend_no_order"]["high_risk"]
        for (camp, ag, term), m in sorted(agg.items(), key=lambda x: -x[1].spend):
            if not term or m.orders > 0:
                continue
            if m.clicks < min_clicks and m.spend < spend_hr:
                continue
            if any(c and c in term for c in self.competitors):
                self._emit(res, Action("搜索词", camp, ag, term, "", "观察", "", "", "【知识库-口径】docs/07 竞品品牌词可作为广告投放选项，不自动否定，由负责人决定是否单独开活动或手动否定", m.brief()))
                continue
            if any(p and p in term for p in self.protected):
                self._emit(res, Action("搜索词", camp, ag, term, "", "观察", "", "", "【用户固定规则】命中自有品牌词/保护词（meandu、pokpet 等），品牌防守词不否定，只观察或单独控竞价", m.brief()))
                continue
            if term in targets_in_group[(camp, ag)]:
                continue  # 精准投放词本身，交给投放对象层降竞价
            trig = f"点击{m.clicks:.0f}≥{min_clicks}" if m.clicks >= min_clicks else f"花费${m.spend:.2f}≥高风险停止线${spend_hr}"
            is_asin = bool(ASIN_RE.match(term))
            rule = "否定该商品定向（Negative ASIN）" if is_asin else "单搜索词点击≥15 无单默认 Negative Exact"
            self._emit(res, Action(
                "搜索词", camp, ag, term.upper() if is_asin else term, "精准" if not is_asin else "商品",
                "加否定-商品" if is_asin else "加否定-精准", "未否定", "Negative Exact" if not is_asin else "Negative ASIN",
                f"【当前报表】{trig} 且 0 单；【用户固定规则】{rule}（search-term-reinvestment.md）",
                m.brief()))

    # ---- 2. 投放对象竞价 ----
    def _window(self, rows: list[PerfRow], days: int) -> list[PerfRow]:
        if not self.last_date or not any(r.date for r in rows):
            return rows
        start = self.last_date - dt.timedelta(days=days - 1)
        return [r for r in rows if r.date and r.date >= start]

    def _suggest_bid(self, m: Metrics, bid: float, direction: str) -> float:
        formula = self.target_cpa * m.cvr if m.cvr else None
        lo, hi = bid * (1 - self.cap), bid * (1 + self.cap)
        if direction == "down":
            # 公式价低于当前价：降到公式价（不超过上限）；否则说明 CPC 已低于出价，只降半幅
            new = max(formula, lo) if formula is not None and formula < bid else bid * (1 - self.cap / 2)
            new = min(new, bid)
        else:
            new = min(formula, hi) if formula is not None and formula > bid else bid
        return round(max(new, self.floor), 2)

    def _targets(self, res: EngineResult, rows: list[PerfRow], settings: Settings, st_rows: list[PerfRow] | None = None) -> None:
        groups: dict[tuple, list[PerfRow]] = defaultdict(list)
        for r in rows:
            groups[(r.campaign, r.ad_group, r.targeting, r.match_type)].append(r)
        # 同一关键词文本在各匹配方式的近 14 天表现（全账户），用于知识库 docs/09 §3 零转化判断
        by_text_mt: dict[str, dict[str, Metrics]] = defaultdict(lambda: defaultdict(Metrics))
        for r in self._window(rows, 14):
            if r.match_type in self.RANK:
                by_text_mt[norm_text(r.targeting)][r.match_type].add(r)
        st_window = self._window(st_rows or [], 14)
        for (camp, ag, target, mt), rs in groups.items():
            m14, m7, m3 = Metrics(), Metrics(), Metrics()
            for r in self._window(rs, 14):
                m14.add(r)
            for r in self._window(rs, 7):
                m7.add(r)
            for r in self._window(rs, 3):
                m3.add(r)
            key = (camp, ag, norm_text(target), mt)
            bid = settings.bids.get(key) or settings.ag_default_bids.get((camp, ag))
            cur = f"${bid:.2f}" if bid else "待补"
            base = Action("投放对象", camp, ag, target, mt, "", cur, "", "", m14.brief())
            nol = no_order_level(m14, self.th)
            if nol and mt in self.RANK:
                # 知识库 docs/09 §3：零转化不一刀切，先看同词在其他匹配方式是否出单
                text = norm_text(target)
                others = {m2: mm for m2, mm in by_text_mt[text].items() if m2 != mt and mm.orders >= self.cfg["min_orders_for_judgement"]}
                if others:
                    where = "、".join(f"{m2} {mm.orders:g}单（CPA ${mm.cpa:.2f}）" for m2, mm in others.items())
                    base.action, base.current, base.new = "暂停", ("启用" if bid else "待补"), "暂停"
                    base.reason = (f"【当前报表】近14天本{mt}匹配 {m14.brief()}，同词在 {where}；"
                                   f"【知识库-口径】docs/09 §3：出单不在本匹配方式 → 停本匹配，把预算转到出单的匹配方式")
                    self._emit(res, base)
                    continue
                words = text.split()
                root_orders = sum(r.orders for r in st_window if words and all(w in r.search_term.split() for w in words))
                if root_orders > 0:
                    nol_note = f"；【知识库-口径】docs/09 §3：词根在搜索词中仍有 {root_orders:g} 单，只降价观察，不停"
                else:
                    nol_note = ""
            else:
                nol_note = ""
            if nol:
                factor = 1 - self.cap if nol == "高风险" else 1 - self.cap / 2
                base.action = "降竞价"
                base.new = f"${max(round(bid * factor, 2), self.floor):.2f}" if bid else "待补"
                base.reason = (f"【当前报表】近14天 {m14.brief()}；【品类阈值】{self.model} 点击<2单/花费<2单 达到{nol}线 → 降竞价"
                               f"{'（上限 ' + format(self.cap, '.0%') + '）' if nol == '高风险' else '（半幅）'}；未直接暂停，先降价再观察{nol_note}")
                self._emit(res, base)
                continue
            if m14.orders < self.cfg["min_orders_for_judgement"]:
                base.action, base.reason = "观察", f"近14天订单 {m14.orders:g} < 2，未达停止线，样本不足只观察"
                self._emit(res, base)
                continue
            lv = level_cpa(m14.cpa, self.th["cpa"])
            trend_bad = m3.cpa is not None and m7.cpa is not None and m3.cpa > m7.cpa * 1.10
            if lv in ("警戒", "高风险"):
                base.action = "降竞价"
                base.new = f"${self._suggest_bid(m14, bid, 'down'):.2f}" if bid else "待补"
                base.reason = (f"【当前报表】近14天 CPA ${m14.cpa:.2f}；【品类阈值】{self.model} CPA {lv}；"
                               f"建议竞价 = {self.target_cpa_src} ${self.target_cpa:g} × CVR {m14.cvr:.1%}，单次下调不超过 {self.cap:.0%}")
            elif lv == "优质" and m14.orders >= 3 and not trend_bad:
                new = self._suggest_bid(m14, bid, "up") if bid else None
                if bid and new and new > bid * 1.05:
                    base.action, base.new = "提竞价", f"${new:.2f}"
                    base.reason = (f"【当前报表】近14天 {m14.orders:g} 单，CPA ${m14.cpa:.2f} 达优质线，近3天未转差；"
                                   f"建议竞价 = {self.target_cpa_src} ${self.target_cpa:g} × CVR {m14.cvr:.1%}，单次上调不超过 {self.cap:.0%}")
                else:
                    base.action, base.reason = "保持", f"CPA ${m14.cpa:.2f} 优质，公式竞价未明显高于当前竞价，保持"
            else:
                why = "近3天 CPA 较7天变差>10%，不提价" if trend_bad else f"CPA {lv}，Bid 合理"
                base.action, base.reason = "保持", why
            self._emit(res, base)

    # ---- 3. 广告位 ----
    def _placements(self, res: EngineResult, rows: list[PerfRow], camp_m: dict, settings: Settings) -> None:
        pc = self.cfg["placement"]
        by_camp: dict[str, dict[str, Metrics]] = defaultdict(lambda: defaultdict(Metrics))
        for r in rows:
            by_camp[r.campaign][r.placement].add(r)
        for camp, pls in by_camp.items():
            total = Metrics()
            for m in pls.values():
                total.spend += m.spend
                total.orders += m.orders
                total.sales += m.sales
                total.clicks += m.clicks
            # 活动整体效果优先用投放对象/搜索词口径（与活动概览一致），没有时才用广告位合计
            basis = camp_m.get(camp) if camp_m.get(camp) and camp_m[camp].clicks else total
            overall = level_cpa(basis.cpa, self.th["cpa"]) if basis.orders >= 2 else ("高风险" if no_order_level(basis, self.th) else "样本不足")
            if overall in ("优质", "正常", "样本不足"):
                res.notes.append(f"广告活动「{camp}」整体 CPA {overall}，按规则不进入广告位优化")
                continue
            for pl, m in pls.items():
                if pl not in ("TOS", "ROS", "PP") or m.clicks < pc["min_clicks"]:
                    continue
                share = m.spend / total.spend if total.spend else 0
                lv = level_cpa(m.cpa, self.th["cpa"]) if m.orders >= 2 else (no_order_level(m, self.th) or "样本不足")
                pct = settings.placement_pct.get((camp, pl))
                cur = f"{pct:g}%" if pct is not None else "待补"
                if lv in ("警戒", "高风险") and share >= pc["bad_share"]:
                    new = 0 if lv == "高风险" else (round(pct / 2) if pct is not None else None)
                    self._emit(res, Action("广告位", camp, "", pl, "", "降广告位溢价", cur,
                                           f"{new:g}%" if new is not None else "待补",
                                           f"【当前报表】活动整体 CPA {overall}；{pl} 花费占比 {share:.0%}，CPA {lv} → 降低该位置溢价"
                                           f"{'到 0' if lv == '高风险' else '一半'}（old-product-promotion.md 广告位规则）", m.brief()))
                elif lv == "优质" and share < pc["good_share"]:
                    new = (pct or 0) + pc["raise_step_pct"]
                    self._emit(res, Action("广告位", camp, "", pl, "", "提广告位溢价", cur, f"{new:g}%" if pct is not None else "待补",
                                           f"【当前报表】{pl} CPA 优质但花费占比仅 {share:.0%} → 有效流量拿得不够，溢价 +{pc['raise_step_pct']}pp", m.brief()))

    # ---- 4. 预算 ----
    def _budgets(self, res: EngineResult, camp_m: dict, settings: Settings, dates: list) -> None:
        bc = self.cfg["budget"]
        days = (dates[-1] - dates[0]).days + 1 if dates else None
        total_cap = self.profile.get("total_daily_budget")
        for camp, m in camp_m.items():
            budget = settings.budgets.get(camp)
            if not budget or not days:
                continue
            avg = m.spend / days
            if avg < budget * bc["limited_ratio"]:
                continue
            lv = level_cpa(m.cpa, self.th["cpa"]) if m.orders >= 2 else "样本不足"
            if lv in ("优质", "正常"):
                new = round(budget * (1 + bc["raise_pct"]), 2)
                note = f"；类目日预算总额 ${total_cap} 需人工核对剩余空间" if total_cap else "；类目日预算总额未确认"
                self._emit(res, Action("广告活动", camp, "", "", "", "加预算", f"${budget:.2f}", f"${new:.2f}",
                                       f"【当前报表】日均花费 ${avg:.2f} ≥ 预算 {bc['limited_ratio']:.0%}（预算受限），CPA {lv} → 加预算 {bc['raise_pct']:.0%}{note}",
                                       m.brief()))
            else:
                res.notes.append(f"广告活动「{camp}」预算受限但 CPA {lv}，不加预算，先优化词和竞价")

    # ---- 5. 出单词拓量（加关键词） ----
    def _harvest(self, res: EngineResult, rows: list[PerfRow], settings: Settings, totals: Metrics) -> None:
        hc = self.cfg["harvest"]
        agg: dict[str, Metrics] = defaultdict(Metrics)
        src: dict[str, set] = defaultdict(set)
        for r in rows:
            if r.search_term and not ASIN_RE.match(r.search_term):
                agg[r.search_term].add(r)
                src[r.search_term].add(f"{r.campaign}/{r.ad_group}")
        targeted = settings.keywords | {norm_text(r.targeting) for r in rows if r.match_type in ("精准", "词组", "广泛")}
        avg_cpa = totals.cpa
        spu = self.profile.get("spu") or "SPU待补"
        op = self.profile.get("operator") or "lulu"
        mult = float(self.cfg.get("new_group_budget_cpa_multiple", 1))
        budget = round(self.th["cpa"]["normal_high"] * mult, 2)
        kb_lo, kb_hi = self.cfg.get("kb_test_budget_cpa_multiple", [3, 5])
        kb_note = (f"；【知识库-口径】测试期参考每活动 {kb_lo}–{kb_hi} 个目标 CPA ≈ "
                   f"${self.target_cpa * kb_lo:.0f}–${self.target_cpa * kb_hi:.0f}/日，审批时可选")
        for term, m in sorted(agg.items(), key=lambda x: -x[1].orders):
            if m.clicks < hc["min_clicks"] or m.orders < hc["min_orders"] or term in targeted:
                continue
            if avg_cpa is not None and m.cpa is not None and m.cpa > avg_cpa:
                continue
            if any(c and c in term for c in self.competitors):
                self._emit(res, Action("新增", "", "", term, "", "观察", "", "",
                                       "【知识库-口径】docs/07 竞品品牌词出单：默认不进手动词表，可作为单独活动的投放选项，由负责人决定", m.brief()))
                continue
            exact = m.clicks >= hc["exact_min_clicks"] and m.orders >= hc["exact_min_orders"]
            mt = "精准" if exact else "词组"
            # 新词竞价：公式价，但不超过该搜索词实际 CPC ×(1+上限)，避免公式把出价抬得远高于真实成交价
            cpc = m.spend / m.clicks if m.clicks else None
            formula = self.target_cpa * (m.cvr or 0)
            bid = round(max(min(formula, cpc * (1 + self.cap)) if cpc else formula, self.floor), 2)
            name = f"{spu}-SP-{term}-{mt}-喂水器-{self.model}-{op}"
            self._emit(res, Action("新增", name, name, term, mt, "加关键词", "未投放", f"Bid ${bid:.2f}，日预算 ${budget:g}",
                                   f"【当前报表】搜索词累计 {m.brief()}，CPA ≤ 链接平均 CPA "
                                   f"{'$' + format(avg_cpa, '.2f') if avg_cpa is not None else '（无）'}，且未单独投放；"
                                   f"来源 {', '.join(sorted(src[term]))}；预算=品类 CPA 正常线上限（{self.model}）×{mult:g}{kb_note}；"
                                   f"【知识库-总纲】属于放量方式 {'S3 精准' if exact else 'S2 长尾/词组承接'}",
                                   m.brief()))
