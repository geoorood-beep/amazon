# 每周交接记录（Grok → 分析方）

每周任务 A 完成后在最上方追加一条，旧记录保留。

分析方（Claude / Codex）收到后：读取本条记录 → 运行 `cd old_product_module && py cli.py --category pet_water_fountain --reports ../categories/pet_water_fountain/ops/weekly/<周>/raw --profile <产品档案JSON>` 生成方案草稿 → 读对应 `weekly/<周>/raw/` 报表复核 → 按 `AGENTS.md` 路由到老品 / 搜索词模块 → 按当前成熟度允许的动作出方案 → 方案报告和执行指令单草稿放进 `weekly/<周>/plan/`，由用户审批后另存为 `execution/<YYYYMMDD>_执行指令单.md`。

## 模板

```text
### <年>-W<周数>（<提交日期>）
- 导出完整度：必须报表 x/6，建议报表 x/4
- 当前成熟度：Lx（上周 Lx）
- 本周补齐：
- 仍缺：
- 需用户确认：
- 请分析方重点看：
- 上次执行回顾：执行 x 行，成功 x，跳过 x（原因）
```

## 记录
