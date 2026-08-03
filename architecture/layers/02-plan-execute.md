# 第 02 层：Plan-and-Execute

## 目标

先冻结输入和判断计划，再生成候选动作；候选、校验和人工执行必须分开。

## 标准流程

```text
冻结输入与版本
→ 数据预处理
→ 数据质量门
→ 领域诊断
→ 候选动作
→ 冲突仲裁
→ 独立 Validator
→ 人工审批
→ 人工执行确认
```

## 阶段状态

- 数据不足或来源冲突：停止在诊断前。
- `DQ_WARNING`：只能观察或 `APPROVAL_REQUIRED`。
- `DQ_BLOCKED`：不得生成执行动作。
- `BLOCKED`：不得进入执行表。
- `AUTO_PASS`：只表示结构和规则校验通过，仍需人工执行。

## 读取

- 数据质量、状态和动作规则：`rules/core/`；
- 领域流程：`rules/domains/`；
- 执行字段：`contracts/action-and-plan.md`；
- 数值：`thresholds/`。
