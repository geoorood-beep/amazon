# 风险与 CDQ 审核

每次 Listing 生成后，都必须通过确定性审核，才算可用。

主要代码：

- `amazon-listing-webapp/lib/audit.ts`
- `amazon-listing-webapp/lib/localListingGenerator.ts`
- `amazon-listing-webapp/lib/aiListingGenerator.ts`

## 风险筛查范围

以下内容都要筛查：

- 用户提示词。
- 表单字段。
- 勾选卖点。
- 运营备注和补充卖点。
- 上传关键词文件。
- 上传风险词文件。
- 图片识别备注。
- 生成后的 Title。
- 生成后的 Item Highlights。
- 生成后的五点。
- 生成后的 Product Description。
- 生成后的 Search Terms。
- 如果有属性 / 变体命名，也要筛查。

## 硬风险类别

必须删除或中性化：

- 竞品品牌和 IP 词。
- ASIN、UPC、EAN、假 ID 占位词。
- 排名、徽章、热门、最高级声明。
- 价格、促销、优惠券、折扣、赠品、包邮声明。
- 保修、保证、退款、满意度、卖家承诺。
- 医疗、疾病、治疗、疗效、动物药品、健康声明。
- 抗菌、杀菌、除菌、消毒、虫害、跳蚤蜱虫等受监管表达，除非有正式证明且平台允许。
- 未证明的安全、无毒、防敏、环保、有机、认证、材质声明。

## 需证明 / 慎用项

这些可以写，但必须有用户确认；没有证明时要在确认项里标出：

- 精确材质等级，如 `304 stainless steel`。
- BPA free、non-toxic、food grade。
- 电池容量和续航。
- 静音 / silent，如果没有分贝或测试条件。
- 感应模式、APP 控制、自动模式、可洗碗机、 waterproof、outdoor use。
- 椅子的承重。
- 地毯的 washable、non slip、fade resistant。

可用谨慎表达：

- `supports about`
- `depending on use`
- `designed for`
- `helps catch visible hair and debris`
- `routine maintenance`

不要写绝对结果。

## 审核清单

必须通过：

- Title <= 75 characters。
- Title 最多 1 个逗号。
- Title 以准确品牌名开头。
- Title 不含品牌外的禁用标点。
- Title 中非豁免词不重复超过 2 次。
- Title 只使用该类目支持的简短事实。
- Item Highlights 115-125 characters。
- Bullet Points 正好 5 条。
- Product Description 默认 1800-2000 English characters，除非用户要求更短。
- Search Terms 小于 250 UTF-8 bytes。
- Search Terms 无分隔符、无品牌、无 ASIN、无重复 root。
- 禁用 / 高危输出命中为 0。
- CDQ 一致性覆盖图片、Title、Item Highlights、五点、描述、Search Terms、属性和变体命名。

任何硬 gate 失败，都要重写失败模块并重新审核。

## 输出报告要求

每次输出都要报告：

- `Search Terms bytes`
- `Keyword embedding summary`
- `Blocked input / risk screening`
- `Forbidden-term check`
- `CDQ consistency check`
- `Needs manual confirmation`

不要隐藏未解决的需证明项，必须直接标出来。
