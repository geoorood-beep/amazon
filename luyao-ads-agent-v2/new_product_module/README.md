# AI广告智能体广告架构设计模块

本目录实现模块一：广告架构设计。模块根据 Rug ASIN、产品属性、ABA 和历史证据生成 Excel 候选架构，不调用 Amazon Ads API。

`--product` 兼容单个产品对象，也支持 `{"products": [...]}` 批量对象。批量模式只读取一次固定 ABA 和历史证据，但每个 ASIN 独立运行规则管线，最后合并到同一份两表工作簿；`ABA选词表` 通过 ASIN 列保持逐行可追溯。

## 运行

```bash
python3 cli.py \
  --product tests/fixtures/product.sop_6_2.json \
  --keywords tests/fixtures/keywords.sop_6_2.csv \
  --rules tests/fixtures/category_rules.sop_6_2_validation.yaml \
  --output tests/fixtures/result.sop_6_2.xlsx
```

固定 Rug 数据模式：

```bash
python3 cli.py \
  --product tests/fixtures/product.sop_6_2.json \
  --aba ../reference/rug-aba/ \
  --history ../reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx \
  --relevance ../reference/rug-relevance/ \
  --search-volume ../reference/rug-search-volume/ \
  --rules config/category_rules.example.yaml \
  --output result.xlsx
```

输出 Excel 固定包含两个 sheet：

- `ABA选词表`：表格下方包含自然段 `判断依据与设计逻辑`，数据源问题和待人工确认原因也在该说明区保留。
- `新广告设置表`：使用七段式广告组命名，并保留人工确认字段。

Phrase / Broad 不再使用“ABA排名分界”。程序先读取 ASIN 相关性，再计算词根月搜索量、Top3 占比和有效查询数，最后结合语义特异度生成候选。`reference/rug-relevance/` 或 `reference/rug-search-volume/` 没有实际数据文件时，程序输出 `MATCH_TYPE_DATA_PENDING` 并不新建广告组。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

## 规则库说明

生产示例规则库是 `config/category_rules.example.yaml`。它标记为 `HUMAN_EXECUTION_ONLY + TEST_ONLY`。其中没有用户确认的数字保留 `null`，程序会把依赖这些字段的关键词或广告结构写入人工确认原因，不会借用其他地毯类型的参数。Rug O<2 停止线尚无可执行 Threshold ID，因此固定为 `BLOCKED_PENDING_THRESHOLD_ID`。

新品没有当前 ASIN 的历史点击或订单时，模块可以进入 `ABA_COLD_START` 候选路径，但只生成 `CANDIDATE_ONLY`：候选必须来自固定 Rug ABA，并同时通过 Rug 类型、至少一项次级属性、阶段、合规和广告状态检查。该路径不伪造点击、订单、CVR、CPA、ACOS 或综合分；Bid、广告位与Amazon后台动作仍需人工确认。存在真实历史样本时，历史辅助路径继续执行已配置的样本量门槛。

V2.0 在任何历史成交、ABA 阶段和评分之前执行产品属性检查：关键词有明确尺寸时必须与本次目标尺寸一致；明确冲突的地毯类型、风格、颜色、材质、形状或图案动物类型直接判为 `不建议投放`，不会进入广告架构。属性字段缺失但关键词写出明确属性时进入人工确认。可在 `attribute_scoring.<属性>.value_aliases` 中扩充类目同义词。

V2.0 同时根据 `size_spec` 自动识别 `runner / doormat / area_rug / round`，不再要求人工先填写 `rug_type`。`2x4`、`3x6`、`3x7`、`4x10`、`4x12` 和所有短边为 `2.5` 的矩形归 `runner`；区域按 `57.5平方英尺` 路由到 `area_small / area_large` 分析阈值档案；圆形在阈值未配置时不借用其他类型。

固定 ABA 适配器只读取每个工作簿的 `广告词库` sheet。同词跨文件冲突时采用保守策略：任一来源存在合规/广告状态风险，或类型、层级、相关度不一致，均进入隔离复核。固定历史文件来自关键词分析汇总，其 legacy `search_term` 字段按 `TARGETING_KEYWORD` 解释，不当作 Amazon Customer Search Term、真实匹配方式或独立成交日期证据。

`tests/fixtures/category_rules.sop_6_2_validation.yaml` 只用于复现 SOP 6.2 两条验收样例。SOP 6.2 与 SOP 4.3.2/4.3.3 存在两处不一致：

- `5x8 vintage blue area rug` 的 ABA 排名 `25,000` 按 4.3.2 的 `0-15单/日` Area Rug 区间 `[60,000, 500,000]` 实际不应直接通过。
验收 fixture 保留一条阶段外词以验证“ABA 超出阶段范围，受限测试”，同时另有尺寸和颜色硬冲突测试验证 V2.0 属性门槛。
