# 新品：广告架构

## 允许

- Phrase；
- 关键词 Broad；
- Auto Close。

## 默认禁止

- Exact；
- Auto Loose；
- Substitutes；
- Complements；
- 竞品或自有 ASIN 定向；
- 未经明确要求的 Product Targeting。

Exact 需要稳定的当前链接搜索词表现，应转入老品规则判断。

## 分组

- 先按 `thresholds/rug/new-product-stage.md` 的 ABA 分组门；
- 同组必须同流量入口、同搜索意图、同属性目的；
- 头部、尺寸、场景、风格和拓词词根不得为了减少广告组而混组；
- 低预算隔离测试必须单独组、单独预算并标记非主投。

Phrase 承接词序稳定的短语和属性长尾；关键词 Broad 只做低 Bid、小预算拓词；Auto 只保留 Close match。Broad 是关键词匹配方式，不得与 Auto Loose 混为一种广告。

## 命名

统一使用：

```text
SPU-广告产品-定向维度-匹配方式-场景分类-尺寸-运营名
```

SPU 不明写 `SPU待补`。智能体输出运营名为 `lulu`。只有单关键词且 ABA 排名可确认时，定向维度可以附大致排名；多词、词根、Auto、类目或 ASIN 不写排名。

排名缩写只作可读命名：千位用 `k`，万位用 `w`，不在名称中复制完整数字。

## 预算和参数

标准最低预算只从 `thresholds/rug/budget-and-isolation.md` 读取。Bid、广告位或风险参数未确认时写待人工配置，不得推算。
