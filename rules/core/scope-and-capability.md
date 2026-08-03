# 核心规则：作用域与能力

## 项目边界

- 唯一允许类目是 Rug / 地毯。
- 固定数据只允许使用 `config/project_scope.json` 白名单路径。
- 非 Rug 任务立即停止并路由到 `/Users/leo/Documents/有它广告智能体`。
- 禁止跨项目读取 ABA、历史效果、流量数据、阈值或对象映射。

## 能力路由

| AdProductType | StrategyProfile | 当前处理 |
|---|---|---|
| SP | `SP_STANDARD_OPTIMIZATION` | `ai_ads/` 只允许 `TEST_ONLY` 结构验证 |
| SP | `SP_COLD_START` | `CAPABILITY_NOT_ACTIVE` |
| SB / SD | 任意 | `UNSUPPORTED_SCOPE` |
| SP | 缺 StrategyProfile | `BLOCKED` |

新品模块可以生成 Rug 新广告人工建议表，但这不等于 V2 `SP_COLD_START` 能力已经激活。

## 运行状态

- 人工执行：允许；
- Amazon API 自动执行：禁止；
- 机器 ACTIVE 规则包：不存在；
- `AUTO_PASS`：不代表已经执行或允许自动执行。
