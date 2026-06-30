# Walmart 类目路由

Walmart 生成必须先判断类目，再加载该类目的 knowledge base。不能用一个类目的关键词表生成另一个类目的 Listing。

## 类目 key 规则

建议使用稳定英文 key：

- `rug`
- `chair`
- `pet_water_fountain`
- 后续新增类目使用小写 snake_case，例如 `dog_leash`、`pet_feeder`、`office_desk`

## 路由输入

判断类目时使用：

- 用户明确给出的类目。
- 产品名称。
- 尺寸 / 规格。
- 图片可见产品类型。
- 当前产品属性和卖点。
- 运营备注。
- 上传的关键词表文件名或 sheet 名。

## 路由输出

类目路由必须输出：

```json
{
  "platform": "walmart",
  "category": "rug",
  "knowledge_base": "category_libraries/rug/walmart_listing_knowledge_base.xlsx",
  "rules": "category_libraries/rug/rules.md",
  "needs_confirmation": []
}
```

如果不能可靠判断类目，停止并要求用户确认；不要默认用 rug 词库生成非 rug 产品。

## 多类目 workbook 加载设计

未来脚本建议支持：

```bash
python scripts/walmart_kb.py prepare \
  --category rug \
  --text-file /absolute/path/current_product.txt \
  --sizes "2x6,5x7,8x10" \
  --top 100 \
  --output /absolute/path/walmart_context.json
```

或者：

```bash
python scripts/walmart_kb.py prepare \
  --workbook /absolute/path/category_libraries/rug/walmart_listing_knowledge_base.xlsx \
  --text-file /absolute/path/current_product.txt \
  --sizes "2x6,5x7,8x10" \
  --top 100 \
  --output /absolute/path/walmart_context.json
```

`scan` 和 `audit` 必须使用同一类目的 workbook，不能 prepare 用 A 类目、audit 用 B 类目。

## 隔离规则

- `selected_keywords` 必须来自当前类目 prepare 结果。
- 不同类目的 Frequency Rank 不能跨类目比较。
- 不同类目的 prohibited terms 都只能作为本类目的审核输入；如果有平台通用风险库，应由脚本合并进当前类目的 context。
- 新类目必须先准备 workbook，再生成 Listing。
