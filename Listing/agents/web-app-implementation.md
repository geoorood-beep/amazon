# Amazon Listing Web App 实现边界

只有当任务涉及本地 Amazon Listing 生成器代码、API、前端展示、关键词高亮或 fallback 生成时，才使用本文件。

## 当前代码入口

本地项目常见路径：

- `amazon-listing-webapp/app/page.tsx`
- `amazon-listing-webapp/app/api/generate/route.ts`
- `amazon-listing-webapp/app/api/listing/generate/route.ts`
- `amazon-listing-webapp/lib/localListingGenerator.ts`
- `amazon-listing-webapp/lib/aiListingGenerator.ts`
- `amazon-listing-webapp/lib/audit.ts`
- `amazon-listing-webapp/lib/categoryKeywordRouting.ts`
- `amazon-listing-webapp/lib/keywordDataParser.ts`
- `amazon-listing-webapp/lib/listingSchema.ts`
- `amazon-listing-webapp/lib/systemPrompt.ts`
- `amazon-listing-webapp/data/categoryKeywordData.json`

如果本机路径变化，先用 `rg --files` 定位，不要按旧路径硬改。

## 必须保留的能力

代码修改不能破坏：

- 类目路由。
- 类目词库隔离。
- 风险词筛查。
- Search Terms byte 计算。
- Search Terms root 去重。
- Title 75 character gate。
- Item Highlights 115-125 character gate。
- Bullet count gate。
- Description character count。
- CDQ audit。
- 关键词绿色高亮。
- API 失败时的本地 fallback 生成。

## API Key 边界

- `OPENAI_API_KEY` 只能在服务端读取。
- 前端不能暴露 API Key。
- 不要把 `.env.local` 打包进可迁移包或 GitHub。
- API quota / billing 错误不能阻塞 Listing 输出；必须回落到本地 SOP 生成。

## 上传文件

上传的关键词表或风险表：

- 只影响当前生成请求。
- 不能自动写回 `categoryKeywordData.json`。
- 必须先通过解析和风险筛查。
- 如果用户明确要求“更新项目词库”，才允许进入数据转换流程，并保留来源文件和校验记录。

## 绿色高亮

生成结果不要让模型返回 HTML。

正确做法：

- 后端返回 plain text Listing。
- 后端或本地生成器返回 `keywordCoverage.used[].keyword`。
- 前端把命中的关键词包成 `<span className="keyword-hit">...</span>`。

这样可以避免模型输出污染 HTML，也能保证高亮和埋词统计一致。

## 审核失败处理

当 `audit.ts` 或同等逻辑发现失败：

- 只重写失败模块。
- 不要重写已经通过且风险为 0 的模块。
- 重新运行 audit。
- 最终回答必须说明仍未解决的 gate 或确认项。

## 打包边界

AGENTS 可迁移包可以包含：

- `AGENTS.md`
- `agents/`
- `knowledge-bases/amazon/`
- 规则说明和安装脚本

不要打包：

- `.env.local`
- API Key
- `node_modules`
- `.next`
- `.DS_Store`
- 临时上传文件
- 用户敏感资料
