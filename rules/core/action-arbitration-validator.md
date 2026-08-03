# 核心规则：动作仲裁与独立 Validator

## 动作仲裁

固定优先级：

```text
数据质量与对象映射
> AdContext 硬约束
> 风险控制
> 本轮主目标
> Campaign 整体判断
> Target / 搜索词 / Placement 局部判断
> 探索性动作
```

规则：

1. 同一对象、同一批次只保留一个主动作。
2. 相反动作不得取平均、随机选择或同时保留。
3. 暂停为主动作时，撤销该对象其他主动作。
4. 高成本风险状态不得同时主动扩量。
5. 新结构与关闭旧结构并存时，先建立承接，再关闭旧结构。
6. 多个动作共同放大风险时形成 Action Pack。
7. 无法安全仲裁时输出观察或 `BLOCKED`。
8. Candidate Action ID 在批次内唯一；辅助动作与主动作使用同一套相反动作和暂停冲突检查。

## 执行字段

每条执行动作必须满足 `contracts/action-and-plan.md`。缺不可变 ID、当前值、目标值、回滚值、快照、Rule ID、Threshold ID 或有效期时，只能降级为建议或阻断。

## Validator

Validator 只检查，不新增或修改动作。输出只有：

- `AUTO_PASS`；
- `APPROVAL_REQUIRED`；
- `BLOCKED`。

`BLOCKED` 不得进入执行表。`APPROVAL_REQUIRED` 必须由人工确认。V2.0 中所有实际实施均为人工执行。

当前 V2.0 的生产保险固定关闭。调用输入中的 `ACTIVE` 状态不能覆盖该保险；生产模式统一增加 `PRODUCTION_EXECUTION_DISABLED` 阻断。
