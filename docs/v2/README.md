# 广告智能体 V2 第一阶段

本目录保存 V2 第一阶段的冻结基线、来源文件和规则裁决记录。L-001 至 L-011 均已进入当前 V2.0 人工执行文档规则；机器规则包仍未激活。

## 当前文件

| 文件 | 用途 |
|---|---|
| `V1.3_BASELINE.md` | V1.3提交、标签、完整归档、哈希和测试结果 |
| `phase1-rule-decisions.yaml` | L-001至L-011机器可读裁决登记表 |
| `第一阶段_P0规则裁决审核稿.md` | 供业务审核的中文裁决说明 |
| `真实数据补充清单.md` | 区分可直接开发项和必须使用真实报表的项目 |
| `V2.0_修复实施记录_20260803.md` | 本轮修复、验证快照、验收结果和剩余阻断项 |
| `V2.0_版本激活记录_20260803.md` | 当前版本定义、继承关系和安全边界 |
| `八层架构拆分记录_20260803.md` | 当前 AGENTS、规则、阈值、合同、知识和历史的物理拆分及校验 |
| `V2.0_第五层外部接入预留_20260803.md` | MCP、API、外部服务器和统一入库位置、状态与启用边界 |
| `V2.0_广告报表聚合工具_20260803.md` | 本地六表聚合程序、工作簿和压力测试验收记录 |
| `source/AI广告Agent完整架构与实施方案_V2.0.md` | 冻结的架构来源 |
| `source/老品广告Agent逻辑漏洞定位清单.md` | 冻结的漏洞来源 |

## 状态边界

- 当前登记表总状态：`DRAFT_REVIEW_ONLY`，因为机器执行唯一规则源、剩余品类阈值和生产 Validator 尚未完成
- 当前执行方式：`HUMAN_EXECUTION_ONLY`
- 当前文档规则：`V2.0`，已纳入 L-001 至 L-011
- V1.3 冻结基线：保持不变
- 机器 ACTIVE 规则包：尚未创建
- V2安全基础模块：`ai_ads/`，状态为`TEST_ONLY`
- Rug 门垫、长条、小区域和大区域的连续阈值已确认；圆形 Rug 阈值仍待维护
- 机器执行的唯一规则源：尚未确定
- Amazon后台自动执行：未启用

## 当前维护入口

`docs/v2/` 保存来源、裁决和实施记录，不是当前规则或阈值真源。人工修改必须进入 `rules/README.md` 或 `thresholds/README.md`；字段进入 `contracts/README.md`；数据源进入 `knowledge/README.md`。

## 校验

使用隔离环境运行：

```bash
.venv/bin/python scripts/validate_phase1_decisions.py
.venv/bin/python scripts/validate_v20_rules.py
.venv/bin/python -m pytest new_product_module/tests ai_ads/tests -q
```

第一条命令只校验裁决登记表、来源哈希和状态边界，不执行广告动作。

第二条命令同时检查 Rug 项目边界、V2 来源 SHA-256、阈值原件 SHA-256、连续阈值摘要、阶段区间、固定工作簿结构以及 `HUMAN_EXECUTION_ONLY + TEST_ONLY` 安全门。
