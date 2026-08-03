# AI广告智能体新品推广模块

本目录实现模块一：新品推广。模块只生成 Excel 建议表，不调用 Amazon Ads API。

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
  --rules config/category_rules.example.yaml \
  --output result.xlsx
```

输出 Excel 固定包含两个 sheet：

- `ABA选词表`：表格下方包含自然段 `判断依据与设计逻辑`，数据源问题和待人工确认原因也在该说明区保留。
- `新广告设置表`：使用七段式广告组命名，并保留人工确认字段。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

## 规则库说明

生产示例规则库是 `config/category_rules.example.yaml`。它标记为 `HUMAN_EXECUTION_ONLY + TEST_ONLY`。其中没有用户确认的数字保留 `null`，程序会把依赖这些字段的关键词或广告结构写入人工确认原因，不会借用其他地毯类型的参数。Rug O<2 停止线尚无可执行 Threshold ID，因此固定为 `BLOCKED_PENDING_THRESHOLD_ID`。

V2.0 在任何历史成交、ABA 阶段和评分之前执行产品属性检查：关键词有明确尺寸时必须与本次目标尺寸一致；明确冲突的地毯类型、风格、颜色、材质、形状或图案动物类型直接判为 `不建议投放`，不会进入广告架构。属性字段缺失但关键词写出明确属性时进入人工确认。可在 `attribute_scoring.<属性>.value_aliases` 中扩充类目同义词。

V2.0 同时根据 `size_spec` 自动识别 `runner / doormat / area_rug / round`，不再要求人工先填写 `rug_type`。`2x4`、`3x6`、`3x7`、`4x10`、`4x12` 和所有短边为 `2.5` 的矩形归 `runner`；区域按 `57.5平方英尺` 路由到 `area_small / area_large` 分析阈值档案；圆形在阈值未配置时不借用其他类型。

固定 ABA 适配器只读取每个工作簿的 `广告词库` sheet。同词跨文件冲突时采用保守策略：任一来源存在合规/广告状态风险，或类型、层级、相关度不一致，均进入隔离复核。固定历史文件来自关键词分析汇总，其 legacy `search_term` 字段按 `TARGETING_KEYWORD` 解释，不当作 Amazon Customer Search Term、真实匹配方式或独立成交日期证据。

`tests/fixtures/category_rules.sop_6_2_validation.yaml` 只用于复现 SOP 6.2 两条验收样例。SOP 6.2 与 SOP 4.3.2/4.3.3 存在两处不一致：

- `5x8 vintage blue area rug` 的 ABA 排名 `25,000` 按 4.3.2 的 `0-15单/日` Area Rug 区间 `[60,000, 500,000]` 实际不应直接通过。
验收 fixture 保留一条阶段外词以验证“ABA 超出阶段范围，受限测试”，同时另有尺寸和颜色硬冲突测试验证 V2.0 属性门槛。
