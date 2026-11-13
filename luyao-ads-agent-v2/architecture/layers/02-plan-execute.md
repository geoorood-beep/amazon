# 第 02 层：Plan-and-Execute

## 目标

先冻结输入和判断计划，再生成候选动作；候选、校验和人工执行必须分开。

## 标准流程

```text
冻结输入与版本
→ Python 确定性预处理与工具回执
→ 数据质量门
→ 构建八层 AGENTS 上下文
→ Codex 领域诊断与候选动作
→ 冲突仲裁
→ 独立 Validator 重建上下文并核对回执
→ 结果页面与工作簿渲染
→ 人工审批
→ 人工执行确认
```

聚合报表任务只运行确定性预处理，不进入 Codex 业务判断。新品候选证据表和 SP 聚合数据包都是输入证据；在 Validator 通过前，不能直接作为最终广告方案展示或下载。

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
