# Amazon 广告 AGENTS 集合

本项目使用“一个总入口 + 多个子 AGENTS”的结构。总入口只负责路由；具体判断规则放在 `agents/` 子文件，避免单个 AGENTS 过长导致读取不完整。

## AGENTS 目录

当用户输入 `AGENTS 目录` 时，必须读取并展示：

`agents/agents-directory.md`

展示时要说明每个 AGENT 能带来什么结果、用户需要输入什么、需要维护什么基础数据、缺失数据会造成什么影响。

新增、删除、改名或调整任何 AGENT 时，必须同步更新 `agents/agents-directory.md`。

## 读取顺序

处理任何亚马逊广告、新品推广、老品推广、搜索词、词根、ABA、类目流量结构、广告位、预算、Bid、否词或新广告搭建任务时，先读本文件，再按任务读取对应子 AGENTS：

1. 新品推广选词与广告架构搭建：读 `agents/new-product-promotion.md`
2. 老品推广总诊断：读 `agents/old-product-promotion.md`
3. 搜索词再投放 / 词根聚合 / ABA 匹配：读 `agents/search-term-reinvestment.md`
4. ABA 类目流量结构与打法判断：读 `agents/category-traffic-strategy.md`
5. 类目历史出单词数据管理：读 `agents/category-history-data.md`
6. 品类阈值标准，包括喂水器和地毯：读 `agents/category data thresholds.md`
7. 输出表格、老广告优化、新广告设置：读 `agents/promo-output-templates.md`

如果任务同时涉及多个模块，按上面顺序合并判断。新品推广和老品推广先判断数据阶段，再选择对应 AGENT。搜索词再投放规则是老品推广 SOP 的子模块，不是总入口。只用 ABA 判断类目流量结构或打法时，先读 `agents/category-traffic-strategy.md`；如果要进一步判断某个具体产品如何投放，再进入新品推广或搜索词模块。

## 默认数据源

默认喂水器 ABA 排名表：

`/Users/leo/Documents/广告智能体 2/reference/ABA喂水器.xlsx`

默认地毯通用 ABA 参考表：

`/Users/leo/Documents/广告智能体 2/reference/通用地毯类目ABA关键词库_202605_v2.xlsx`

当地毯新品推广任务只提供产品信息、历史搜索词或出单词表，且没有提供新的 ABA 表时，默认使用地毯通用 ABA 表。不同地毯类型必须按 `agents/new-product-promotion.md` 中的 sheet 映射读取，不要混用同一个 ABA 池。

用户当前任务提供新的 ABA 表时，以新 ABA 表优先。

类目历史出单词数据固定目录：

`/Users/leo/Documents/广告智能体 2/reference/category-history/`

类目流量结构数据固定目录：

`/Users/leo/Documents/广告智能体 2/reference/category-traffic/`

已固定类目流量数据：

- 办公椅 / 人体工程学办公椅：`reference/category-traffic/office_chair/`

当用户提供历史搜索词、历史出单词、同类历史数据，或任务需要判断“同类历史成交证据”时，读取 `agents/category-history-data.md`。ABA 表和历史出单词表必须分开管理，不能把 ABA 词库当作历史出单词数据。

类目历史出单词数据只用于选词中的历史参考、同类可复用词推荐和新品/新广告候选词补充。它不是老品推广方案的数据源报表。老品推广诊断、预算、Bid、广告位、否词、暂停、放量等动作，必须使用当前链接 / 当前 Campaign / 当前广告组的真实报表。

## 总原则

- 不要只看 ACOS 直接调预算、Bid、暂停或放量。
- 先判断数据有效性、样本量、观察周期、对象映射，再给动作。
- 输出必须说明：观察周期、核心指标、命中规则、数据充分度、为什么没有选择其他动作。
- 新品推广一般没有稳定 CPA / CVR / ACOS 阈值参考；优先看同类历史成交证据、ABA 阶段、产品属性匹配和低预算验证。
- 新品阶段不能用短期 CPA / CVR / ACOS 直接强判暂停、否词或放量；如果当前链接已有稳定广告数据，应转入老品推广。
- 老品推广必须同时考虑：老广告如何优化、新广告是否需要新增/并入/重建。
- 老品推广输入报表名称必须按 `agents/old-product-promotion.md` 的“老品输入报表命名标准”输出，不要使用泛化报表名替代。
- 搜索词投放优先从历史出单搜索词和词根表现出发，ABA 主要用于判断市场容量、稳定流量和长期排名机会。
- ABA 类目流量结构判断只回答入口数量、头部集中度和打法方向，不等于具体产品选词；产品级承接必须结合产品属性、阶段和历史出单证据。
- 当前链接自己的搜索词数据优先级最高；类目历史出单词数据只作为同类历史参考，不能覆盖当前链接真实表现。
- 类目历史出单词数据不得作为老品方案的数据源报表；只能作为“选词参考 / 新增词候选 / 可复用词池”使用。
