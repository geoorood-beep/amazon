import csv
import datetime as dt
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from cli import main  # noqa: E402
from engine.loaders import load_reports  # noqa: E402
from engine.rules import FountainEngine  # noqa: E402
from engine.xlsx_reader import read_table  # noqa: E402

CFG = json.loads((HERE.parent / "categories" / "pet_water_fountain" / "engine.json").read_text(encoding="utf-8"))
END = dt.date(2026, 11, 15)
CAMP_A = "WF10-SP-自动-喂水器-10L-lulu"
CAMP_B = "WF10-SP-cat water fountain-精准-喂水器-10L-lulu"
CAMP_C = "WF10-SP-water fountain for cats-广泛-喂水器-10L-lulu"
CAMP_D = "WF10-SP-dog water fountain-词组-喂水器-10L-lulu"


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def spread(total_clicks, total_spend, total_orders, total_sales, days=14):
    """把总量平均摊到最近 days 天，返回 [(date, clicks, spend, orders, sales)]。"""
    out = []
    for i in range(days):
        d = END - dt.timedelta(days=i)
        out.append((d.isoformat(), total_clicks / days, total_spend / days, (total_orders if i == 0 else 0), (total_sales if i == 0 else 0)))
    return out


def build_reports(d: Path) -> None:
    # 领星中文表头：搜索词每日明细
    st = []
    def add_st(camp, ag, target, mt, term, clicks, spend, orders, sales):
        for date, c, s, o, sa in spread(clicks, spend, orders, sales):
            st.append([date, camp, ag, target, mt, term, c * 10, round(c, 3), round(s, 3), o, sa])
    add_st(CAMP_A, "自动组", "close-match", "-", "pet water dispenser plastic", 20, 18, 0, 0)       # 否词
    add_st(CAMP_A, "自动组", "close-match", "-", "b0abcdefgh", 16, 14, 0, 0)                         # 否 ASIN
    add_st(CAMP_A, "自动组", "close-match", "-", "meandu fountain", 30, 25, 0, 0)                    # 自有品牌词
    add_st(CAMP_A, "自动组", "close-match", "-", "pokpet water fountain", 18, 15, 0, 0)               # 自有品牌词
    add_st(CAMP_A, "自动组", "close-match", "-", "stainless steel cat fountain", 40, 30, 4, 160)     # 拓量
    add_st(CAMP_A, "自动组", "close-match", "-", "fountain small", 5, 4, 0, 0)                       # 样本不足
    add_st(CAMP_A, "自动组", "close-match", "-", "selene dog water fountain", 20, 18, 0, 0)          # 竞品品牌词
    write_csv(d / "SP搜索词-按词-每日明细_20261102_20261115.csv",
              ["日期", "广告活动", "广告组", "投放", "匹配类型", "用户搜索词", "曝光量", "点击", "花费", "广告订单", "广告销售额"], st)

    # Amazon 英文表头：投放对象报告
    tg = []
    def add_tg(camp, ag, target, mt, clicks, spend, orders, sales):
        for date, c, s, o, sa in spread(clicks, spend, orders, sales):
            tg.append([date, camp, ag, target, mt, c * 10, round(c, 3), round(s, 3), o, sa])
    add_tg(CAMP_B, "精准组", "cat water fountain", "EXACT", 30, 32, 0, 0)          # 高风险无单 -> 降 20%
    add_tg(CAMP_B, "精准组", "dog water fountain", "EXACT", 30, 54, 2, 80)         # CPA 27 警戒
    add_tg(CAMP_B, "精准组", "pet fountain stainless", "EXACT", 50, 45, 5, 200)    # CPA 9 优质 -> 提价
    add_tg(CAMP_A, "自动组", "close-match", "-", 111, 91, 4, 160)
    add_tg(CAMP_C, "广泛组", "water fountain for cats", "BROAD", 80, 80, 2, 80)  # 活动 C 整体 CPA 40 高风险
    add_tg(CAMP_D, "词组组", "dog water fountain", "PHRASE", 31, 25, 0, 0)        # 词组零转化，同词精准出单 -> 暂停词组
    add_tg(CAMP_D, "广泛组", "pet fountain stainless", "BROAD", 40, 20, 4, 160)   # 广泛优质要提价，但会高于同词精准 -> 拦截
    write_csv(d / "SP投放对象报告_20261102_20261115.csv",
              ["Date", "Campaign Name", "Ad Group Name", "Targeting", "Match Type", "Impressions", "Clicks", "Spend",
               "7 Day Total Orders (#)", "7 Day Total Sales "], tg)

    # 广告位：活动 B 整体达标（不进入广告位优化）；活动 C 整体高风险，TOS 占比大且差
    write_csv(d / "SP广告位报告_20261102_20261115.csv",
              ["Campaign Name", "Placement", "Impressions", "Clicks", "Spend", "7 Day Total Orders (#)", "7 Day Total Sales "],
              [[CAMP_B, "Top of Search on-Amazon", 900, 60, 90, 2, 80],
               [CAMP_B, "Detail Page on-Amazon", 500, 30, 20, 1, 40],
               [CAMP_C, "Top of Search on-Amazon", 900, 60, 60, 1, 40],
               [CAMP_C, "Detail Page on-Amazon", 300, 20, 20, 1, 40]])

    # 设置表（扁平格式）
    write_csv(d / "Campaign设置表_20261116.csv",
              ["广告活动", "广告组", "投放", "匹配类型", "竞价", "每日预算", "搜索结果顶部溢价", "商品页面溢价"],
              [[CAMP_B, "", "", "", "", 20, 50, 0],
               [CAMP_B, "精准组", "cat water fountain", "精准", 1.00, "", "", ""],
               [CAMP_B, "精准组", "dog water fountain", "精准", 1.50, "", "", ""],
               [CAMP_B, "精准组", "pet fountain stainless", "精准", 0.80, "", "", ""],
               [CAMP_A, "", "", "", "", 6, "", ""],
               [CAMP_A, "自动组", "close-match", "自动", 0.90, "", "", ""],
               [CAMP_C, "", "", "", "", 30, 40, 0],
               [CAMP_C, "广泛组", "water fountain for cats", "广泛", 1.00, "", "", ""],
               [CAMP_D, "", "", "", "", 15, "", ""],
               [CAMP_D, "词组组", "dog water fountain", "词组", 1.20, "", "", ""],
               [CAMP_D, "广泛组", "pet fountain stainless", "广泛", 0.85, "", "", ""]])


def run(maturity, profile_extra=None):
    tmp = Path(tempfile.mkdtemp())
    build_reports(tmp)
    profile = {"model": "10L", "spu": "WF10", "brand_terms": ["meandu", "pokpet"]}
    profile.update(profile_extra or {})
    rep = load_reports(tmp)
    res = FountainEngine(CFG, profile, maturity).run(rep)
    return rep, res


def find(res, action, target):
    hits = [a for a in res.actions if a.action == action and a.target.lower() == target.lower()]
    return hits[0] if hits else None


class EngineTest(unittest.TestCase):
    def test_reports_classified_and_mapped(self):
        rep, _ = run("L2")
        self.assertEqual(rep.warnings, [])
        self.assertEqual(set(rep.files), {"st_daily", "targeting", "placement", "settings"})

    def test_negative_exact_and_asin(self):
        _, res = run("L2")
        neg = find(res, "加否定-精准", "pet water dispenser plastic")
        self.assertIsNotNone(neg)
        self.assertTrue(neg.executable)
        self.assertIsNotNone(find(res, "加否定-商品", "B0ABCDEFGH"))
        self.assertIsNone(find(res, "加否定-精准", "fountain small"))

    def test_protected_term_not_negated(self):
        _, res = run("L2")
        for term in ("meandu fountain", "pokpet water fountain"):
            self.assertIsNone(find(res, "加否定-精准", term))
            self.assertIsNotNone(find(res, "观察", term))

    def test_no_order_high_risk_bid_down_full_cap(self):
        _, res = run("L2")
        a = find(res, "降竞价", "cat water fountain")
        self.assertEqual((a.current, a.new), ("$1.00", "$0.80"))
        self.assertFalse(a.needs_confirm)  # 自动上限是用户确认的策略，不逐条二次确认

    def test_warning_cpa_bid_formula(self):
        _, res = run("L2", {"bid_cap_pct": 0.2, "target_cpa": 25})
        a = find(res, "降竞价", "dog water fountain")
        # 目标 CPA 25 × (2/30) = 1.67 >= 当前 1.50 -> 半幅下调 10% -> 1.35
        self.assertEqual(a.new, "$1.35")
        self.assertFalse(a.needs_confirm)

    def test_raise_bid_blocked_until_L3(self):
        _, res = run("L2", {"bid_cap_pct": 0.2})
        a = find(res, "提竞价", "pet fountain stainless")
        self.assertFalse(a.executable)
        self.assertIn("L2", a.blocked_by)
        _, res3 = run("L3", {"bid_cap_pct": 0.2})
        a3 = find(res3, "提竞价", "pet fountain stainless")
        self.assertTrue(a3.executable)
        self.assertEqual(a3.new, "$0.96")  # 公式 25*0.1=2.5，封顶 +20%

    def test_placement_only_when_campaign_bad(self):
        _, res = run("L2")
        pls = [a for a in res.actions if a.layer == "广告位"]
        self.assertEqual([(a.campaign, a.target, a.current, a.new) for a in pls], [(CAMP_C, "TOS", "40%", "0%")])
        self.assertTrue(any(CAMP_B in n and "不进入广告位优化" in n for n in res.notes))
        # 知识库：广告位门槛待补充，只做人工复核，不进指令单
        self.assertFalse(pls[0].executable)
        self.assertIn("第十四章", pls[0].blocked_by)

    def test_competitor_brand_term_not_negated(self):
        _, res = run("L2")
        self.assertIsNone(find(res, "加否定-精准", "selene dog water fountain"))
        self.assertIn("docs/07", find(res, "观察", "selene dog water fountain").reason)

    def test_zero_conversion_phrase_paused_when_exact_converts(self):
        _, res = run("L2")
        a = [x for x in res.actions if x.campaign == CAMP_D and x.target == "dog water fountain"][0]
        self.assertEqual((a.action, a.current, a.new), ("暂停", "启用", "暂停"))
        self.assertTrue(a.executable and a.needs_confirm)
        self.assertIn("docs/09", a.reason)

    def test_bid_ladder_blocks_broad_above_exact(self):
        _, res = run("L3", {"bid_cap_pct": 0.2})
        broad = [x for x in res.actions if x.campaign == CAMP_D and x.target == "pet fountain stainless"][0]
        self.assertEqual(broad.action, "提竞价")
        self.assertFalse(broad.executable)
        self.assertIn("docs/05", broad.blocked_by)  # 广泛 $1.02 会高于精准 $0.96

    def test_harvest_budget_shows_kb_test_range(self):
        _, res = run("L3", {"target_cpa": 20})
        a = find(res, "加关键词", "stainless steel cat fountain")
        self.assertIn("日预算 $25", a.new)
        self.assertIn("$60–$100/日", a.reason)

    def test_new_keyword_bid_capped_by_cpc(self):
        _, res = run("L3", {"bid_cap_pct": 0.2})
        a = find(res, "加关键词", "stainless steel cat fountain")
        self.assertTrue(a.new.startswith("Bid $0.90"))  # CPC 0.75 × 1.2，而不是公式价 2.50

    def test_harvest_only_L3(self):
        _, res2 = run("L2")
        self.assertFalse(find(res2, "加关键词", "stainless steel cat fountain").executable)
        _, res3 = run("L3")
        a = find(res3, "加关键词", "stainless steel cat fountain")
        self.assertTrue(a.executable and a.needs_confirm)
        self.assertEqual(a.campaign, "WF10-SP-stainless steel cat fountain-精准-喂水器-10L-lulu")  # 点击>20 且订单>=4 -> 精准

    def test_brand_terms_protected_even_if_profile_omits(self):
        _, res = run("L2", {"brand_terms": []})
        self.assertIsNone(find(res, "加否定-精准", "pokpet water fountain"))

    def test_auto_target_cpa_from_history(self):
        # 投放对象合计：花费 347、订单 17 -> 历史 CPA 20.41，落在 10L 优质线 20 ~ 正常线上限 25 之间
        _, res = run("L2", {"target_cpa": "auto", "bid_cap_pct": "auto"})
        self.assertIn("链接历史CPA $20.41", " ".join(a.reason for a in res.actions))

    def test_auto_target_clamped_and_fallback(self):
        from engine.rules import Metrics
        eng = FountainEngine(CFG, {"model": "10L"}, "L2")
        eng._resolve_target(Metrics(clicks=500, spend=600, orders=15))   # 历史 CPA 40 -> 拉回正常线上限 25
        self.assertEqual(eng.target_cpa, 25)
        eng = FountainEngine(CFG, {"model": "10L"}, "L2")
        eng._resolve_target(Metrics(clicks=500, spend=150, orders=15))   # 历史 CPA 10 -> 不低于优质线 20
        self.assertEqual(eng.target_cpa, 20)
        eng = FountainEngine(CFG, {"model": "5L"}, "L2")
        eng._resolve_target(Metrics(clicks=50, spend=60, orders=3))      # 不足 10 单 -> 5L 正常线上限 30
        self.assertEqual(eng.target_cpa, 30)
        eng = FountainEngine(CFG, {"model": "10L", "target_cpa": 18}, "L2")
        eng._resolve_target(Metrics(clicks=500, spend=600, orders=15))   # 人工设定优先
        self.assertEqual(eng.target_cpa, 18)

    def test_L0_has_no_executable(self):
        _, res = run("L0")
        self.assertEqual([a for a in res.actions if a.executable], [])

    def test_cli_writes_outputs(self):
        tmp = Path(tempfile.mkdtemp())
        raw = tmp / "raw"
        raw.mkdir()
        build_reports(raw)
        prof = tmp / "p.json"
        prof.write_text(json.dumps({"model": "10L", "spu": "WF10"}), encoding="utf-8")
        self.assertEqual(main(["--reports", str(raw), "--profile", str(prof), "--maturity", "L2"]), 0)
        report = (tmp / "plan" / "方案报告.md").read_text(encoding="utf-8")
        order = (tmp / "plan" / "执行指令单草稿.md").read_text(encoding="utf-8")
        self.assertIn("判断依据与设计逻辑", report)
        self.assertIn("`SP广告商品报告` | 缺失", report)
        self.assertIn("| 1 | US |", order)
        self.assertIn("审批状态：`待审批`", order)
        self.assertIn("# 喂水器 10L 老品广告方案", report)
        self.assertIn("categories/pet_water_fountain/thresholds.md", report)
        self.assertIn("- 类目：pet_water_fountain", order)

    def test_cli_category_flag_and_unopened_category(self):
        tmp = Path(tempfile.mkdtemp())
        raw = tmp / "raw"
        raw.mkdir()
        build_reports(raw)
        prof = tmp / "p.json"
        prof.write_text(json.dumps({"model": "10L"}), encoding="utf-8")
        self.assertEqual(main(["--category", "pet_water_fountain", "--reports", str(raw), "--profile", str(prof), "--maturity", "L2"]), 0)
        # 待建品类没有 engine.json：明确报错，不借用其他品类阈值
        with self.assertRaises(SystemExit) as cm:
            main(["--category", "pet_feeder", "--reports", str(raw), "--profile", str(prof)])
        self.assertIn("pet_feeder", str(cm.exception.code))

    def test_template_engine_json_has_no_thresholds(self):
        from cli import load_category_config
        with self.assertRaises(SystemExit) as cm:
            load_category_config("_template")
        self.assertIn("models 为空", str(cm.exception.code))

    def test_fountain_engine_json_matches_thresholds_md(self):
        md = (HERE.parent / "categories" / "pet_water_fountain" / "thresholds.md").read_text(encoding="utf-8")
        for model in ("10L", "5L"):
            cpa = CFG["models"][model]["cpa"]
            self.assertIn(f"$" + format(cpa["normal_high"], "g"), md)
            self.assertIn(f"$" + format(cpa["high_risk"], "g"), md)

    def test_xlsx_reader(self):
        tmp = Path(tempfile.mkdtemp()) / "t.xlsx"
        with zipfile.ZipFile(tmp, "w") as z:
            z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                       '<sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                       '<si><t>广告活动</t></si><si><t>点击</t></si><si><t>花费</t></si><si><t>A</t></si></sst>')
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                       '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'
                       '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2"><v>12</v></c><c r="C2"><v>3.5</v></c></row>'
                       '</sheetData></worksheet>')
        self.assertEqual(read_table(tmp), [{"广告活动": "A", "点击": 12, "花费": 3.5}])


class VersionConsistencyTest(unittest.TestCase):
    """GROK.md / VERSION.md / AGENTS.md / README.md 版本号必须一致，VERSION.md 当前版本必须写“Grok 须知”。"""

    def test_version_consistency(self):
        import re
        root = HERE.parent
        version_md = (root / "VERSION.md").read_text(encoding="utf-8")
        current = re.search(r"当前版本：`(V\d+\.\d+)`", version_md).group(1)
        grok = (root / "GROK.md").read_text(encoding="utf-8")
        self.assertIn(f"（UTA-amazon-ads {current}）", grok.splitlines()[0])
        self.assertIn(f"本文件版本：**{current}**", grok)
        self.assertIn(f"版本：{current}（读自 VERSION.md", grok)
        for name in ("AGENTS.md", "README.md"):
            text = (root / name).read_text(encoding="utf-8")
            self.assertEqual(text.splitlines()[0], f"# UTA-amazon-ads {current}", name)
            self.assertIn(f"当前版本：`{current}`", text, name)
        section = version_md.split(f"## {current} 新增范围", 1)[1].split("\n## ", 1)[0]
        self.assertIn("### Grok 须知", section)


if __name__ == "__main__":
    unittest.main()
