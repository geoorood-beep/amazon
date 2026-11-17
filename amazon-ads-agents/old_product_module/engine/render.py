"""把引擎结果写成：方案报告.md（给人看）、执行指令单草稿.md（给 Grok）、actions.csv。"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .loaders import MISSING_IMPACT, REPORT_NAMES, LoadedReports
from .rules import Action, EngineResult

ORDER = ["加否定-精准", "加否定-商品", "降竞价", "降广告位溢价", "暂停", "提竞价", "提广告位溢价", "加预算", "加关键词", "观察", "保持"]


def _cell(s: object) -> str:
    return str(s).replace("|", "/").replace("\n", " ")


def _sort(actions: list[Action]) -> list[Action]:
    return sorted(actions, key=lambda a: (ORDER.index(a.action) if a.action in ORDER else 99, a.campaign, a.ad_group))


def render_report(res: EngineResult, rep: LoadedReports, profile: dict, maturity: str, engine) -> str:
    exe = [a for a in res.actions if a.executable]
    blocked = [a for a in res.actions if not a.executable and a.blocked_by]
    watch = [a for a in res.actions if a.action in ("观察", "保持")]
    missing = [k for k in REPORT_NAMES if k not in rep.files]
    t = res.totals
    asin = ", ".join(profile.get("asins", [])) or "未提供"
    conf = "高" if not missing and maturity in ("L3", "L4") else ("中" if "targeting" in rep.files and "settings" in rep.files else "低")

    L: list[str] = []
    L.append(f"# 喂水器 {engine.model} 老品广告方案（引擎草稿）\n")
    L.append(f"生成时间：{dt.datetime.now():%Y-%m-%d %H:%M}　数据成熟度：`{maturity}`　{res.window_note}\n")
    L.append("> 本报告由 `old_product_module` 按 AGENTS 规则确定性计算。分析方（Claude / Codex）应在此基础上复核搜索词相关性、补充判断依据，再交用户审批。\n")

    L.append("## 产品策略摘要\n")
    L.append(f"- ASIN / SKU：{asin}；型号：{engine.model}；SPU：{profile.get('spu') or 'SPU待补'}")
    L.append(f"- 整体（{('投放对象报告' if 'targeting' in rep.files else '搜索词报告')}口径）：{t.brief()}")
    L.append(f"- 竞价口径：{engine.target_cpa_src} ${engine.target_cpa:g}；单次调整上限 {engine.cap:.0%}"
             f"（{engine.cap_src}）")
    L.append(f"- 可执行动作 {len(exe)} 条；成熟度或缺数据拦截 {len(blocked)} 条；观察/保持 {len(watch)} 条")
    L.append(f"- 数据置信度：{conf}\n")

    L.append("## 已导入报表与缺失影响\n")
    L.append("| 标准报表名 | 状态 | 缺失影响 |")
    L.append("|---|---|---|")
    for k, name in REPORT_NAMES.items():
        L.append(f"| `{name}` | {'已导入：' + rep.files[k] if k in rep.files else '缺失'} | {'' if k in rep.files else MISSING_IMPACT[k]} |")
    for w in rep.warnings:
        L.append(f"\n- ⚠️ {w}")
    if rep.unclassified:
        L.append(f"\n- ⚠️ 未识别的文件（文件名不标准，需人工确认）：{', '.join(rep.unclassified)}")
    L.append("")

    L.append("## 广告活动概览\n")
    L.append("| 广告活动 | 指标 | CPA 等级 | ACOS 等级 | 日预算 |")
    L.append("|---|---|---|---|---|")
    for c in res.campaign_summary:
        L.append(f"| {_cell(c['campaign'])} | {c['metrics'].brief()} | {c['cpa_level']} | {c['acos_level']} | {'$%.2f' % c['budget'] if c['budget'] else '待补'} |")
    L.append("")

    def table(title: str, rows: list[Action], extra: bool = False) -> None:
        L.append(f"## {title}\n")
        if not rows:
            L.append("无。\n")
            return
        L.append("| 层级 | 广告活动 | 广告组 | 对象 | 匹配 | 动作 | 当前值 | 新值 | 二次确认 | 原因 |" + (" 拦截原因 |" if extra else ""))
        L.append("|---|---|---|---|---|---|---|---|---|---|" + ("---|" if extra else ""))
        for a in _sort(rows):
            L.append(f"| {a.layer} | {_cell(a.campaign)} | {_cell(a.ad_group)} | {_cell(a.target)} | {a.match_type} | {a.action} | {a.current} | {a.new} | "
                     f"{'是' if a.needs_confirm else '否'} | {_cell(a.reason)} |" + (f" {a.blocked_by} |" if extra else ""))
        L.append("")

    table("可执行动作（进入执行指令单草稿）", exe)

    L.append("### 判断依据与设计逻辑\n")
    neg = sum(1 for a in exe if a.action.startswith("加否定"))
    down = sum(1 for a in exe if a.action == "降竞价")
    up = sum(1 for a in exe if a.action == "提竞价")
    L.append(
        f"【当前报表】本次只使用当前链接的真实报表（{', '.join(rep.files.values()) or '无'}），{res.window_note}。"
        f"【品类阈值/用户固定规则】阈值取 `agents/category data thresholds.md` 喂水器 {engine.model}：CPA 正常线上限 ${engine.th['cpa']['normal_high']}，"
        f"高风险 ${engine.th['cpa']['high_risk']}，点击<2单高风险 {engine.th['clicks_no_order']['high_risk']} 次，花费<2单高风险 ${engine.th['spend_no_order']['high_risk']}；"
        f"搜索词点击≥15 且 0 单默认 Negative Exact。本次生成否定 {neg} 条、降竞价 {down} 条、提竞价 {up} 条。"
        f"先否定和降价（止损）再考虑放量，订单不足 2 单的对象一律只观察，不用短期 ACOS 直接暂停。"
        f"【人工输入/预算目标】{engine.target_cpa_src}；竞价上限 {engine.cap:.0%}（{engine.cap_src}）；"
        f"成熟度 {maturity} 只解锁：{', '.join(sorted(engine.unlocked)) or '无'}。"
        f"【缺失数据】{('缺 ' + '、'.join(REPORT_NAMES[k] for k in missing)) if missing else '必须报表齐全'}；广告商品层诊断、小时花费、跨 SPV/SB/SBV 拓量本版引擎未实现，需分析方人工补充。\n"
    )

    table("被拦截的动作（成熟度未解锁或缺当前值，不进入指令单）", blocked, extra=True)

    if res.notes:
        L.append("## 其他说明\n")
        L.extend(f"- {n}" for n in res.notes)
        L.append("")

    L.append(f"## 观察 / 保持（{len(watch)} 条）\n")
    if watch:
        L.append("| 层级 | 广告活动 | 广告组 | 对象 | 匹配 | 动作 | 指标 | 原因 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for a in watch[:200]:
            L.append(f"| {a.layer} | {_cell(a.campaign)} | {_cell(a.ad_group)} | {_cell(a.target)} | {a.match_type} | {a.action} | {_cell(a.metrics)} | {_cell(a.reason)} |")
    L.append("")
    return "\n".join(L)


ORDER_ACTION = {"加否定-精准": "加否定-精准", "加否定-商品": "加否定-商品", "降竞价": "改竞价", "提竞价": "改竞价",
                "降广告位溢价": "改广告位溢价", "提广告位溢价": "改广告位溢价", "加预算": "改预算", "加关键词": "新建广告组", "暂停": "暂停"}


def render_order(res: EngineResult, profile: dict, maturity: str, plan_ref: str, max_rows: int = 30) -> str:
    exe = _sort([a for a in res.actions if a.executable])
    site = profile.get("site", "US")
    L = [
        f"# {dt.date.today():%Y%m%d} 执行指令单（草稿）\n",
        "- 类目：pet_water_fountain",
        f"- 方案来源：`{plan_ref}`",
        f"- 数据截止日期：{getattr(res, 'last_date', '') or '见方案报告'}",
        f"- 当前成熟度：{maturity}",
        "- 审批状态：`待审批`（用户审批后改为 `已审批`）",
        "- 审批人：",
        "- 审批日期：\n",
        "## 规则\n",
        "- 只执行 `审批 = 通过` 的行；不要的行把 `审批` 改成 `删除`。",
        "- `当前值` 必须与领星页面一致才执行，否则跳过（见 `agents/grok-operator.md` B2）。",
        "- `需二次确认 = 是` 的行执行前必须在对话中再获得用户确认。",
        f"- 单次最多执行 {max_rows} 行；本草稿共 {len(exe)} 行{'，超出部分分批' if len(exe) > max_rows else ''}。\n",
        "## 指令\n",
        "| 行号 | 店铺/站点 | 广告活动 | 广告组 | 对象 | 匹配方式 | 动作 | 当前值 | 新值 | 需二次确认 | 原因 | 审批 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, a in enumerate(exe, 1):
        L.append(f"| {i} | {site} | {_cell(a.campaign)} | {_cell(a.ad_group)} | {_cell(a.target)} | {a.match_type} | {ORDER_ACTION.get(a.action, a.action)} | "
                 f"{a.current} | {a.new} | {'是' if a.needs_confirm else '否'} | {_cell(a.reason)} | |")
    return "\n".join(L) + "\n"


def write_csv(res: EngineResult, path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["层级", "广告活动", "广告组", "对象", "匹配方式", "动作", "当前值", "新值", "需二次确认", "可执行", "拦截原因", "指标", "原因"])
        for a in _sort(res.actions):
            w.writerow([a.layer, a.campaign, a.ad_group, a.target, a.match_type, a.action, a.current, a.new,
                        "是" if a.needs_confirm else "否", "是" if a.executable else "否", a.blocked_by, a.metrics, a.reason])
