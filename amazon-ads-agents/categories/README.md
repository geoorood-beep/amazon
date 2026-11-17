# 品类注册表

UTA-amazon-ads 按“通用规则 + 通用知识 + 品类层”三层组织。本目录是品类层：**每个品类一个目录**，放该品类自己的数字和数据。通用打法规则在 `agents/`，通用广告方法论在 `knowledge/ads-framework/`，两者对所有品类通用，换品类不改。

Grok / 分析方收到任务时，先在下表找到品类 key，再按“状态”决定能做什么。

| 品类 | key | 别名（用户可能这么说） | 状态 | 能做什么 |
|---|---|---|---|---|
| 宠物喂水器 | `pet_water_fountain` | 喂水器、饮水机、water fountain、猫喂水器、狗喂水器 | **已开通** | 取数、分析、出方案、执行 |
| 宠物喂食器 | `pet_feeder` | 喂食器、自动喂食器、feeder | 待建 | 只按通用规则给建议，并列出开通缺什么 |
| 智能猫厕所 | `smart_litter_box` | 猫厕所、猫砂盆、自动猫砂盆、litter box | 待建 | 同上 |

地毯（Rug）由同仓库的 `luyao-ads-agent-v2/` 管理，不在本注册表内；本目录 `agents/` 中保留的地毯规则仅作历史参考。

## 状态定义

| 状态 | 条件 | 允许 |
|---|---|---|
| 待建 | 只有目录占位 | 通用规则建议；输出“开通清单” |
| 知识中 | `category.md` 和 `knowledge/` 已有内容，但缺阈值或数据仓 | 选词、架构建议；不出执行指令单 |
| 已开通 | 下面“开通标准”全部满足 | 全流程：取数 → 引擎 → 方案 → 审批 → 执行 |

## 开通标准（从“待建”到“已开通”）

1. `category.md` 品类卡填完：型号 / 规格、自有品牌词、竞品品牌词、在投 ASIN、负责人口径。
2. `thresholds.md` 有 CPA / CVR / ACOS 分级和点击<2单、花费<2单停止线（至少一个型号）。
3. `engine.json` 的阈值与 `thresholds.md` 一致，`brand_terms`、`competitor_brand_terms` 已填。
4. `ops/` 建好（从 `_template/ops/` 复制），`ops/README.md` 成熟度从 L0 开始。
5. `knowledge/` 至少有一份准词表或历史出单词（只做选词参考）。
6. 在本表把状态改为“已开通”，并在 `VERSION.md` 记录。

## 新增品类步骤

1. 复制 `_template/` 为 `categories/<新key>/`（key 用英文小写下划线）。
2. 按模板逐个填写文件。
3. 在本表加一行。
4. 运行引擎测试确认配置能加载：`cd old_product_module && py cli.py --category <新key> --reports <报表目录> --profile <档案>`。

## 每个品类目录的固定结构

```text
categories/<key>/
├── category.md      品类卡：产品形态、型号、品牌词、竞品词、在投 ASIN、负责人口径、状态
├── thresholds.md    品类阈值（唯一权威来源）
├── engine.json      规则引擎配置（阈值数字、品牌词、竞品词、预算倍数、成熟度解锁）
├── knowledge/       品类知识：准词表、初版架构、首推词表、西柚周扫描（只做选词和架构参考）
├── benchmarks/      行业基准与自有历史（V1.5，引擎每周自动生成 基准线_<型号>.md / latest_<型号>.json）
└── ops/             运营数据仓：领星周报表、产品档案、缺失项、执行指令单、改动历史
```
