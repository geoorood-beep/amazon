# 关键词库契约

当前项目的唯一打包关键词 / 风险数据源是：

`amazon-listing-webapp/data/categoryKeywordData.json`

不要把词库内容复制到 agent Markdown 里。Markdown 只定义用法，JSON 才是真正数据源。

## 预期数据结构

每个类目应类似：

```ts
{
  categories: Record<string, string[]>,
  keywordLibrary: Array<{
    term: string,
    aba?: number | null,
    zh?: string,
    topClickShare?: number | null,
    topConversionShare?: number | null
  }>,
  forbiddenTerms: string[],
  label?: string,
  sourceFiles?: string[]
}
```

## 当前打包类目

预期 key：

- `rug`
- `chair`
- `pet_water_fountain`

当前项目中观察到的数据量：

- `rug`：7 个关键词分组，836 行关键词，962 个风险 / 禁用词。
- `chair`：3 个关键词分组，1123 行关键词，1511 个风险 / 禁用词。
- `pet_water_fountain`：3 个关键词分组，458 行关键词，183 个风险 / 禁用词。

如果这些数量变化，不要马上判断为数据丢失，先检查源表转换逻辑。

## 源文件

Skill 侧参考文件在：

`/Users/leo/.codex/skills/listing/references/`

项目 app 侧当前源文件包括：

- `amazon-listing-webapp/data/source/amazon-chair-forbidden-risk-library.xlsx`
- `amazon-listing-webapp/data/source/pet-water-fountain-keyword-forbidden-library.xlsx`

除非代码改动，否则 Web App 运行时仍以生成后的 app JSON 为准。

## 上传文件合并规则

API 可以通过以下文件解析上传的关键词 / 风险文件：

- `amazon-listing-webapp/lib/keywordDataParser.ts`
- `amazon-listing-webapp/app/api/generate/route.ts`

规则：

- 上传的关键词文件，只影响当前这次生成。
- 上传的风险词文件，也只影响当前这次生成。
- 上传文件仍必须走同样的风险筛查。
- 不要把临时上传的数据写回打包 JSON，除非用户明确要求更新项目词库。

## 关键词选择规则

- ABA rank 是流量证据，不等于可以写进文案。
- 当产品事实不支持时，相关性优先于流量。
- 生成前移除竞品品牌。
- 产品不是配件时，移除纯配件搜索词。
- 移除未确认的材质、护理、功能、认证、健康、安全、保证类词。
- Search Terms 按 root 去重，超过 250 bytes 时移除低优先级 token。

## 风险词处理

风险词数据是确定性 gate 输入。

- 禁用词和高危词不能出现在面向客户的输出中。
- 需证明 / 慎用词只有在用户确认或提供证明时才能写；未附证明时必须进入 `Needs manual confirmation`。
- 不要在 Listing 输出里重复被屏蔽的原始风险词。
- 如果用户是为了排查风险而问某个词，可以在 Listing 模块之外直接说明。
