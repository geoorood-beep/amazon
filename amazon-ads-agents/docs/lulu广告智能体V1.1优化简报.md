# lulu 广告智能体 V1.1 优化简报

版本日期：2026-07-07

## 一、版本定位

V1.1 是在原有新品推广、老品推广、搜索词再投放和品类阈值规则上的一次规则固化升级。重点不是新增一个单独模块，而是把今天确认过的广告命名、预算、Rug 输入、动物图案匹配、历史词库、否词隔离和老品拓量逻辑固定到 AGENTS 体系里。

## 二、已固定优化项

### 1. 广告组命名规则统一

固定命名格式：

```text
SPU-广告产品-定向维度-匹配方式-场景分类-尺寸-运营名
```

智能体输出方案时，运营名统一写 `lulu`；人工已明确运营名时使用人工运营名。单关键词广告组可在关键词后标注 ABA 大致排名，例如 `runner rug(4k)`、`area rug(1.8w)`；多个词、词根、类目、Auto 或 ASIN 定向不写 ABA 排名。

### 2. 标准最低日预算改为 CPA 口径

新广告、新品广告组、老品新增或重建广告组的标准最低日预算，统一按对应类目 / 型号 / 尺寸的 CPA 正常线上限设置，不再按 CPC 推算。

如果类目缺少 CPA 阈值，预算必须写 `待补CPA阈值` 或 `待人工配置`，不得编造。

### 3. Rug 新品输入字段收敛

Rug 类目新品广告需要输入的信息，固定按 `新品基础信息输入模版_Rug类目` 的 `产品信息表` 字段：

- `ASIN/SKU`
- `运营`
- `地毯区域`
- `尺寸`
- `材质`
- `颜色`
- `风格`
- `预算（USD/日）`
- `目标订单阶段`
- `图案动物类型`

用户问“新品广告需要输入哪些信息”时，不再默认列出系统侧 ABA 表字段、功能、人群/宠物、是否冷启动等过多字段。

### 4. Rug 动物图案关键词强匹配

如果 Rug 产品图案是具体动物，必须使用 `图案动物类型` 做强匹配。该字段可由用户手动输入，也可由图片识别得到。

规则边界：

- tiger 图案只能匹配 tiger 相关动物词。
- zebra / leopard / cowhide 等其他动物词不得随意推荐。
- 动物类型不明确时，不得推荐具体动物 ABA 关键词。

### 5. Rug 历史出单词库固定

已把冬豚、岚风两份 Rug 关键词分析历史数据入库到：

```text
reference/category-history/rug/
```

标准化文件：

```text
reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx
```

该历史库只用于 Rug 新品选词、新广告候选词和搜索词复用参考，不能替代当前链接真实报表做老品诊断、否词、暂停、降 Bid、预算或广告位动作。

### 6. Rug ABA 关键词库替换为四个场景文件

旧默认地毯通用 ABA 表不再作为默认调用入口。V1.1 当前默认调用：

```text
reference/rug-aba/
```

固定文件：

- `area_rug_ABA关键词库_202605_v8.xlsx`
- `bathroom_rugs_ABA关键词库_202605.xlsx`
- `kitchen_rugs_ABA关键词库_202605_v2.xlsx`
- `outdoor_rug_ABA关键词库_202605_v2.xlsx`

调用规则：

- 只读取每个文件的 `广告词库` sheet。
- 不读取 `说明`、`汇总`、`Listing词库`、`否定禁用`、`类型_*` 等其他 sheet。
- 按产品地毯区域和场景选择对应文件，不把四个文件全量混成一个无场景候选池。
- 旧 `reference/通用地毯类目ABA关键词库_202605_v2.xlsx` 仅作历史备份。

### 7. Rug 高流量核心隔离否词

Rug 新品 Auto / Broad / Phrase 增加高流量核心词精准否定隔离规则：

```text
推荐层级=P1/P2
且 ABA排名<=11000
否定方式=Negative Exact
```

执行边界：

- Auto Close：从当前产品对应广告词库筛选命中阈值的词，加入 `Negative Exact`。
- Broad：先判断 Broad 可能匹配出的词，再筛选命中阈值的词加入 `Negative Exact`。
- Phrase：先判断 Phrase 可匹配出的前后加词集合，再筛选命中阈值的词加入 `Negative Exact`。
- 这是流量隔离，不是低相关否定，不默认做 `Negative Phrase`。
- 其他类目不能套用 Rug 阈值；未维护隔离阈值时，只输出 `该类目高流量核心隔离阈值待配置`。

### 8. 老品优质出单词跨广告产品拓量

新增老品拓量策略：出单效果好、达到优质线标准且稳定的投放词，可以从 SP 复制验证到其他广告产品。

进入跨广告产品拓量的硬条件：

- 当前链接真实报表验证，不能只用类目历史词。
- 观察周期至少覆盖 `7-14` 天。
- 广告订单 `>=3`。
- 聚合点击 `>=30`。
- CPA / ACOS 至少一个达到类目优质线，另一个不能超过正常线。
- CVR 不低于类目正常线。
- 近 3 天没有明显转差。
- 出单花费占比 `>=25%`。

拓量分级：

| 等级 | 判定 | 动作 |
|---|---|---|
| A档 | 达到优质线，样本足，近 3 天稳定 | 保留原 SP，新增 SPV / SB / SBV 复制验证 |
| B档 | 有出单但只到正常线，或样本不足 | 只做 SP 内部 Phrase / Broad / Exact 再投放 |
| C档 | 订单少、效率不稳或 CVR 不足 | 观察、控 Bid，不拓量 |

示例：`area rug` 的 SP Phrase 表现好，可以新增同词 Phrase 逻辑的 SPV、SB、SBV；如果实际订单来自 `washable area rug 5x7` 等长尾搜索词，则优先复制真实出单长尾词或稳定词根，而不是机械复制 `area rug`。

## 三、主要修改文件

- `AGENTS.md`
- `README.md`
- `VERSION.md`
- `agents/agents-directory.md`
- `agents/new-product-promotion.md`
- `agents/old-product-promotion.md`
- `agents/search-term-reinvestment.md`
- `agents/category data thresholds.md`
- `agents/category-history-data.md`
- `agents/promo-output-templates.md`
- `reference/category-history/README.md`
- `reference/category-history/rug/`
- `reference/rug-aba/`

## 四、使用边界

- 新品阶段不能用短期 CPA / CVR / ACOS 强判暂停、否词或放量。
- 老品动作必须使用当前链接 / 当前 Campaign / 当前广告组真实报表。
- 类目历史出单词只做选词参考，不做老品优化动作的数据源。
- Rug ABA 选词默认只读 `reference/rug-aba/` 四个文件中的 `广告词库` sheet。
- 缺 CPA 阈值时不能编预算。
- 缺 SPV / SB / SBV 视频素材、品牌资质、Store 或落地页时，不能生成可执行跨广告产品拓量行。
