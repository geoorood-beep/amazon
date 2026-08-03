# Rug 阈值来源清单

## 已确认原件

- 文件：`reference/category-threshold/confirmed/20260731_V1.4_人工阈值回填原件.xlsx`
- SHA-256：`f2419724adc24ffe4ed6c134a08ab18355d06dc8151c9f81c00c23e007688387`
- 确认日期：`2026-07-31`
- 人工确认编号：`THR-001`
- 已确认：Rug 门垫、长条、小区域、大区域的 CVR / ACOS / CPA 连续互斥区间。
- 暂缓：圆形 Rug。
- 未形成可执行 Threshold ID：O<2 点击/花费停止线。

## 归因门

- 人工确认编号：`THR-301`
- 值与规则：见 `governance.md`。

## 机器状态

```text
execution_mode = HUMAN_EXECUTION_ONLY
machine_rule_status = TEST_ONLY
```

`new_product_module/config/category_rules.example.yaml` 是派生的 TEST_ONLY 配置，不是独立真源。其阈值来源和 SHA-256 必须与本清单一致。
