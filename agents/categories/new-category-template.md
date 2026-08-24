# Amazon 新类目模板

新增 Amazon Listing 类目时，复制本模板为：

`agents/categories/<category-key>.md`

类目 key 使用小写 snake_case，例如：

- `pet_feeder`
- `dog_crate`
- `standing_desk`

## 类目边界

说明什么产品走这个类目，什么产品不走。

必须包含：

- 英文触发词。
- 中文触发词。
- SKU / ASIN / 品牌线索，如果有。
- 与相邻类目的区别。

## 词库

运行时应使用：

`amazon-listing-webapp/data/categoryKeywordData.json` -> `<category-key>`

AGENTS 完整包可携带来源文件：

`knowledge-bases/amazon/source/<category-key>-keyword-forbidden-library.xlsx`

以及转换后文件：

`knowledge-bases/amazon/generated/<category-key>-keyword-library.csv`
`knowledge-bases/amazon/generated/<category-key>-forbidden-risk-terms.csv`
`knowledge-bases/amazon/generated/<category-key>-library-summary.md`

不要在 Markdown 中复制长词库。

## 产品名

列出允许进入 Title 的核心产品名。

示例：

- `Pet Feeder`
- `Automatic Pet Feeder`
- `Dog Crate`

只用当前产品事实支持的产品名，不要为了埋词换成不准确产品名。

## 可进 Title 的短属性

只列短、可证明、用户确认的属性。

示例：

- 容量。
- 颜色。
- 材质。
- 供电方式。
- 适配对象。

高风险、需要证明或容易被误解的属性不要默认放 Title。

## 关键词处理

必须说明：

- 哪些关键词是核心词。
- 哪些是场景词。
- 哪些是配件词，产品不是配件时必须排除。
- 哪些词需要证据。
- 哪些竞品 / IP / ASIN 类词必须拦截。

## 五点主题

列出本类目默认 5 个 Bullet 主题。

1. 产品身份、规格和对象。
2. 核心结构或材质。
3. 核心功能。
4. 日常使用、清洁或维护。
5. 包装清单、适配说明或确认项。

每条主题都必须绑定产品事实，不能用泛泛模板填充。

## 风险注意

列出本类目不能写或需要证明的声明。

常见风险：

- 医疗 / 疾病 / 治疗。
- 安全保证。
- 认证。
- BPA free / non-toxic / food grade。
- 防水 / 户外。
- 保修 / 保证 / 退款。
- 排名 / best seller。

## 验证用例

新增类目后至少用 1 个代表产品验证：

- 类目路由正确。
- 关键词库加载正确。
- 风险词命中为 0。
- Title <= 75 characters。
- Search Terms < 250 bytes。
- 输出包含人工确认项。
