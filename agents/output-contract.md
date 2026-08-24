# Amazon Listing 输出契约

每次 Amazon Listing 生成必须按本文件输出。用户明确要求简版时，可以省略审计明细，但内部仍要按同样规则检查。

## 标准输出顺序

1. `Title`
2. `Item Highlights`
3. `Bullet Points`
4. `Product Description`
5. `Search Terms`
6. `Search Terms bytes`
7. `Keyword embedding summary`
8. `Blocked input / risk screening`
9. `Forbidden-term check`
10. `CDQ consistency check`
11. `Needs manual confirmation`

## Title

要求：

- 只输出 1 个 Title，除非用户给了多变体。
- 最多 75 English characters。
- 目标 70-75 characters，但不要为了凑长度堆词。
- 最多 1 个英文逗号。
- 必须以准确品牌名开头。
- 使用当前类目的准确产品名。
- 只写已确认、短、可证明的事实。

不能写：

- 竞品品牌。
- 排名、促销、保修、保证、医疗、安全、认证、未证明材质。
- 不是本产品的配件词。
- 无证据支持的 absolute claim。

## Item Highlights

要求：

- 输出 1 条。
- 目标 115-125 English characters。
- 用于承接 Title 放不下但有搜索价值的确认事实。
- 不写被拦截词、竞品词或未确认声明。

使用方式：

- Rug：可以承接 style、pattern、color、low pile、easy care、high traffic 等确认事实。
- Chair：可以承接 support、seat、headrest、armrest、footrest、room fit 等确认事实。
- Pet water fountain：可以承接 capacity、bowl/tank material、flow mode、filter、battery、quiet operation 等确认事实。

## Bullet Points

要求：

- 正好 5 条。
- 每条一个主题。
- 每条自然埋 1-3 个安全关键词 root。
- 不机械重复同一句型。
- 不用平台高风险词换一种说法继续表达同一风险含义。

默认主题：

1. 产品身份、规格、对象、场景。
2. 结构、材质、外观或核心体验。
3. 功能模式、调节方式、供电方式或使用方式。
4. 清洁、维护、日常使用。
5. 包装清单、适配说明、人工确认项或安装使用提示。

如果某个主题无产品事实支撑，改写为更保守的使用说明，不要编造。

## Product Description

要求：

- 默认 1800-2000 English characters。
- 用户要求短版时可以缩短，但要保持事实完整。
- 面向买家自然阅读。
- 覆盖产品身份、规格、对象、场景、确认功能和维护说明。
- 不要为了说明风险而在正文里重复风险原词。

## Search Terms

要求：

- 小于 250 UTF-8 bytes。
- lowercase。
- 空格分隔。
- 不使用逗号、竖线、分号、括号、促销标点。
- 不含品牌名、竞品名、ASIN、UPC、EAN。
- 不含风险词。
- 不重复 root。
- 优先放安全、高相关、Title 未完整覆盖的词。

Root 去重规则：

1. lowercase。
2. 标点转空格。
3. 拆成长短合理的 searchable roots。
4. 合并单复数、连字符和空格变体。
5. 保留更高优先级的首次出现。
6. 超过 250 bytes 时，从低相关或已覆盖 token 开始删除。

## Keyword Embedding Summary

必须列出：

- target keyword。
- 使用模块。
- 选择理由。
- safe / blocked / excluded 状态。

不要把被屏蔽词算进埋词率。

## Risk And CDQ Sections

`Blocked input / risk screening`：

- 说明是否发现风险输入。
- 写风险类别和处理方式。
- 不在客户文案模块里重复风险原词。

`Forbidden-term check`：

- 标出输出命中数。
- 目标必须是 0。

`CDQ consistency check`：

- 覆盖 Title、Item Highlights、五点、描述、Search Terms、图片事实、属性和变体命名。

`Needs manual confirmation`：

- 列出所有可写但缺证明的事实。
- 包括精确材质等级、电池容量、续航、静音、认证、安全、承重、洗护方式等。
