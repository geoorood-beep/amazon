#!/usr/bin/env python3
"""validate.py 回归测试。运行: python3 tests/run_tests.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate import validate  # noqa: E402

BASE_BULLETS = [
    "Water Level Window: A clear window shows how much water is left in the tank.",
    "Removable Parts: The lid and bowl lift off for rinsing at the sink.",
    "Plug-In Power: The pump runs from the included power adapter.",
    "Two Flow Modes: Switch between a stream and a bubbling flow.",
    "Pack Contents: One fountain, one adapter and one spare filter.",
]
BASE_DESC = ("This fountain holds water for a cat at home.\n\n"
             "Rinse the parts at the sink and refill the tank when the window shows low water.")


def mk(**kw):
    d = {
        "title": "Brand Cat Water Fountain 2L",
        "highlights": "Bowl and tank sizes listed on the product page",
        "bullets": list(BASE_BULLETS),
        "description": BASE_DESC,
        "keywords": [],
    }
    d.update(kw)
    return d


def hard(rep, needle):
    return any(needle in m for m in rep["hard_fail"])


def warn(rep, needle):
    return any(needle in m for m in rep["warnings"])


FAILS = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


# 0 基线
r = validate(mk())
check("基线无硬性失败", not r["hard_fail"])

# 1 标题边界 74/75/76
for n, exp in ((74, False), (75, False), (76, True)):
    r = validate(mk(title="x" * n))
    check("标题 %d 字符 超限=%s" % (n, exp), hard(r, "标题") == exp and hard(r, "超过 75") == exp)

# 2 亮点边界 124/125/126
for n, exp in ((124, False), (125, False), (126, True)):
    r = validate(mk(highlights="y" * n))
    check("亮点 %d 字符 超限=%s" % (n, exp), hard(r, "亮点") == exp)

# 3 五点数量
check("四条五点失败", hard(validate(mk(bullets=BASE_BULLETS[:4])), "五点数量"))
check("六条五点失败", hard(validate(mk(bullets=BASE_BULLETS + ["Extra Point: More text here."])), "五点数量"))

# 3b 五点合计 1000 / 1001
def bl_total(lens):
    return ["Point %d: %s" % (i + 1, "x" * (n - len("Point %d: " % (i + 1)))) for i, n in enumerate(lens)]
r = validate(mk(bullets=bl_total([200, 200, 200, 200, 200])))
check("五点合计 1000 通过", r["stats"]["bullets_total"] == 1000 and not hard(r, "五点合计"))
r = validate(mk(bullets=bl_total([200, 200, 200, 200, 201])))
check("五点合计 1001 失败", r["stats"]["bullets_total"] == 1001 and hard(r, "五点合计"))
r = validate(mk(bullets=bl_total([257, 100, 100, 100, 100])))
check("单条 257 失败", hard(r, "第 1 条"))

# 4 加粗不计入字符数
t = "**" + "x" * 30 + "** " + "y" * 44          # 去加粗后 30+1+44 = 75
r = validate(mk(title=t))
check("加粗不计入字符数(75 通过)", r["stats"]["title_len"] == 75 and not hard(r, "超过 75"))

# 5 嵌套短语计数：dog water fountain 在三条五点中各出现一次 -> 合计 3 > 2
bl = list(BASE_BULLETS)
bl[0] = "Electric Style: The electric dog water fountain runs from the included adapter."
bl[1] = "Quiet Claim Check: The quiet dog water fountain pump sits inside the tank."
bl[2] = "Metal Bowl: The stainless steel dog water fountain bowl lifts out for cleaning."
r = validate(mk(bullets=bl, keywords=[{"phrase": "dog water fountain", "core": True}]))
check("核心词在五点出现 3 次判失败", hard(r, "核心词") and hard(r, "bullets"))

# 6 被词隔开不算同一连续短语
bl = list(BASE_BULLETS)
bl[3] = "Dog Sized: A water fountain for dogs with a wide bowl."
r = validate(mk(bullets=bl, keywords=[{"phrase": "dog water fountain", "core": True}]))
check("water fountain for dogs 不计入 dog water fountain", not hard(r, "核心词"))

# 7 词边界与大小写
r = validate(mk(description="Do not catch the ball.\n\nCAT beds are sold elsewhere. A cat naps.",
                keywords=["cat"]))
check("词边界: catch 不计, CAT/cat 各计一次", r["stats"]["keywords_covered"] == 1
      and not r["stats"]["keywords_missing"])
r = validate(mk(title="Brand Water Fountain 2L", description="Do not catch the ball.\n\nNothing else here.", keywords=["cat"]))
check("词边界: 仅有 catch 则未覆盖", r["stats"]["keywords_missing"] == ["cat"])

# 8 加粗标记错误
check("未闭合加粗失败", hard(validate(mk(title="Brand **Cat Water Fountain")), "未闭合"))
check("加粗断词失败", hard(validate(mk(title="Brand **Cat**s Fountain")), "断词"))
check("嵌套/空格加粗失败", hard(validate(mk(title="**a **Cat** b** Fountain")), "加粗"))

# 9 标题禁用字符与品牌豁免
check("标题含 ! 失败", hard(validate(mk(title="Brand Cat Fountain!")), "禁用字符"))
check("品牌内字符豁免", not hard(validate(mk(title="Br!nd Cat Fountain", brand="Br!nd")), "禁用字符"))

# 10 标题单词重复
check("标题单词重复 3 次失败", hard(validate(mk(title="Cat Fountain Cat Bowl Cat Dish")), "出现 3 次"))
check("标题单复数折叠", hard(validate(mk(title="Cat Cats Cat Fountain")), "出现 3 次"))
check("标题冠词/介词例外", not hard(validate(mk(title="Water for Cats and for Dogs for Pets")), "出现"))

# 11 最长匹配加粗
kw = ["water fountain", "dog water fountain"]
r = validate(mk(title="Brand **dog water fountain** 2L", keywords=kw))
check("最长匹配加粗无警告", not warn(r, "未按最长匹配") and not warn(r, "未加粗"))
r = validate(mk(title="Brand dog **water fountain** 2L", keywords=kw))
check("短词加粗被警告", warn(r, "未加粗") or warn(r, "未按最长匹配"))

# 12 五点结构
bl = list(BASE_BULLETS)
bl[0] = "No colon here at all just a sentence about the tank."
check("五点缺冒号失败", hard(validate(mk(bullets=bl)), "结构"))

# 13 价格 / 外链
check("价格符号失败", hard(validate(mk(description="Only $9.\n\nSecond paragraph here.")), "价格"))
check("外链失败", hard(validate(mk(description="See https://x.com\n\nSecond paragraph here.")), "外链"))

# 14 详情段数
check("详情 1 段失败", hard(validate(mk(description="Only one paragraph here.")), "段"))

# 15 猫狗错路由
r = validate(mk(species="cat", description="A bowl for dogs.\n\nSecond paragraph here."))
check("species=cat 出现 dogs 警告", warn(r, "另一对象"))

# 16 五点序号去除
r = validate(mk(bullets=["%d. %s" % (i + 1, b) for i, b in enumerate(BASE_BULLETS)]))
check("带序号的五点正常解析", not hard(r, "结构") and r["stats"]["bullet_lens"][0] == len(BASE_BULLETS[0]))

print("\n失败 %d 项" % len(FAILS))
sys.exit(1 if FAILS else 0)
