# AI广告智能体新品推广模块

本目录按 `~/Desktop/CODEX_新品模块实现方案.md` 实现模块一：新品推广。模块只生成 Excel 建议表，不调用 Amazon Ads API。

## 运行

```bash
/Users/leo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 cli.py \
  --product tests/fixtures/product.sop_6_2.json \
  --keywords tests/fixtures/keywords.sop_6_2.csv \
  --rules tests/fixtures/category_rules.sop_6_2_validation.yaml \
  --output tests/fixtures/result.sop_6_2.xlsx
```

输出 Excel 包含四个 sheet：

- `产品策略摘要`
- `订单阶段关键词选择结果`
- `新广告如何设置`
- `待人工确认`

## 测试

```bash
/Users/leo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s tests -v
```

## 规则库说明

生产示例规则库是 `config/category_rules.example.yaml`。其中没有 SOP 明确数字的字段保留 `null`，程序会把依赖这些字段的关键词或广告结构写入 `待人工确认`，不会借用其他地毯类型的参数。

`tests/fixtures/category_rules.sop_6_2_validation.yaml` 只用于复现 SOP 6.2 两条验收样例。SOP 6.2 与 SOP 4.3.2/4.3.3 存在两处不一致：

- `5x8 vintage blue area rug` 的 ABA 排名 `25,000` 按 4.3.2 的 `0-15单/日` Area Rug 区间 `[60,000, 500,000]` 实际不应直接通过。
- `modern large rug` 的分项分数按 `60%/15%/15%/5%/5%` 公式计算为 `79`，但 SOP 6.2 表格写的是 `69.5`。

验收 fixture 为了对齐文档要求，保留 SOP 6.2 表格结果；生产配置仍按阶段表和公式执行。
