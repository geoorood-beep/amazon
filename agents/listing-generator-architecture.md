# Amazon Listing 生成器 AGENTS 架构

本文件把旧 `$listing` 生成器固定成 AGENTS 架构。它定义运行边界、数据层、规则层和发布状态，不直接保存长词库内容。

## 目标

当用户要求生成或审核 Amazon Listing 时，AGENTS 必须能独立指导以下工作：

- 判断平台是 Amazon，而不是 Walmart 或 Wayfair。
- 判断产品类目。
- 只加载当前类目的关键词库和风险库。
- 按 ABA 流量和产品相关性选词。
- 生成 Title、Item Highlights、Bullet Points、Product Description、Search Terms。
- 做风险筛查、Search Terms byte 检查、CDQ 一致性审核。
- 标出需人工确认项。

## 分层

### L0 平台层

入口：`AGENTS.md`

职责：

- 先分 Amazon / Walmart / Wayfair。
- 阻止跨平台规则混用。
- Amazon 任务才进入本架构。

### L1 类目层

入口：

- `agents/category-routing.md`
- `agents/categories/*.md`

职责：

- 把产品路由到 `rug`、`chair`、`pet_water_fountain` 或未来新增类目。
- 定义本类目可用产品名、Title 短属性、五点主题、风险注意事项。
- 阻止跨类目混用高流量关键词。

### L2 数据层

入口：`agents/keyword-library-contract.md`

职责：

- 定义关键词库、风险库、来源文件和上传文件的结构。
- 明确词库是候选池，不是自动文案。
- 规定 ABA rank、相关性和风险筛查的优先级。

### L3 生成层

入口：

- `agents/listing-generation.md`
- `agents/output-contract.md`

职责：

- 把已确认产品事实分配到各 Listing 模块。
- 控制 Title 长度、Item Highlights 长度、五点数量、Description 目标长度、Search Terms byte 限制。
- 输出关键词埋入总结、风险筛查和人工确认项。

### L4 审核层

入口：`agents/risk-cdq-audit.md`

职责：

- 对用户输入、上传数据、图片备注和生成结果做风险筛查。
- 对 Search Terms 做 byte、分隔符、品牌、ASIN 和 root 去重检查。
- 确认 CDQ 一致性。
- 失败模块必须重写后再交付。

### L5 实现层

入口：`agents/web-app-implementation.md`

职责：

- 指导本地 Amazon Listing Web App 的代码修改。
- 保护 API Key 只留在服务端。
- 保留本地 fallback 生成、绿色关键词高亮、CDQ audit 和 Search Terms 逻辑。

## 数据流

```text
用户输入 / 图片 / 上传文件
  -> 输入标准化
  -> 风险预筛
  -> 平台路由
  -> 类目路由
  -> 加载当前类目词库和风险库
  -> 关键词评分
  -> Listing draft
  -> 确定性 audit
  -> PASS 输出 / FAIL 重写失败模块
```

## 发布状态

- `DATA_BLOCKED`：缺少类目、品牌、产品类型或词库无法加载。
- `DRAFT_READY`：文案已生成，但还没有通过完整 audit。
- `REWRITE_REQUIRED`：至少一个硬 gate 失败，只重写失败模块。
- `REVIEW_READY`：全部硬 gate 通过，但仍有需人工确认项。
- `APPROVED`：全部硬 gate 通过，且没有阻塞型确认项。

默认不要把 `REVIEW_READY` 说成完全可发布。只要存在材质等级、电池续航、静音测试、认证、安全等未证明项，就必须明示。

## 迁移边界

旧 `$listing` skill 中的规则已经拆入本 AGENTS：

- 类目路由：`agents/category-routing.md`
- 关键词 / 风险库：`agents/keyword-library-contract.md`
- 生成规则：`agents/listing-generation.md`
- 输出格式：`agents/output-contract.md`
- 风险 / CDQ：`agents/risk-cdq-audit.md`
- Web App：`agents/web-app-implementation.md`

不要再把 `SKILL.md` 当作唯一规则来源。后续改规则时，优先改 AGENTS；如果还保留 skill，只把 skill 当触发入口或兼容层。
