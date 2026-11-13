# Walmart Listing 生成流程

Walmart 生成必须走 prepare -> draft JSON -> audit。不能直接自由写完就交付。

## Step 1: 当前产品输入

只收集当前产品：

- 图片可见事实。
- 用户给出的属性。
- 尺寸 / 规格。
- 材质、背面、护理方式等需确认属性。
- 请求卖点。
- OCR 文本。
- 竞品参考。

不要继承上一轮产品事实。

## Step 2: 写入临时输入文件

把当前产品信息写入 UTF-8 文本，例如：

```text
brand: KUETH
category: rug
sizes: 2x6,5x7,8x10
color: pink
material: user-provided polyester
confirmed selling points: machine washable, low pile
scenarios: living room, bedroom, home office
notes: ...
```

## Step 3: prepare

当前 skill 的命令形态：

```bash
python scripts/walmart_kb.py prepare \
  --text-file /absolute/path/current_product.txt \
  --sizes "2x6,5x7,8x10" \
  --top 100 \
  --output /absolute/path/walmart_context.json
```

多类目版本应增加 `--category` 或 `--workbook`，但输出 contract 不变。

必须完整读取 context JSON，并确认：

- `knowledge_status.ready` 为 `true`。
- keyword / Frequency Rank / conditional note / prohibited-term counts 非 0。
- `input_scan.pass` 为 `true`。
- 每个 size 都有 type decision 或该类目等价 decision。
- `selected_keywords` 非空。

如果失败，停止并报告缺失数据或风险类别，不复述 blocked raw terms。

## Step 4: Draft JSON

草稿必须保存为 JSON：

```json
{
  "titles": [{"size": "2x6", "title": "..."}],
  "description": "...",
  "key_features": ["...", "...", "...", "...", "..."]
}
```

规则：

- 每个 supplied size 输出一个 title。
- 只使用当前产品证据支持的事实。
- Listing body 和 audit 信息分开。
- 不把分数、解释、删除记录写进 Listing 正文。

## Step 5: audit

当前 skill 的命令形态：

```bash
python scripts/walmart_kb.py audit \
  --listing-json /absolute/path/draft.json \
  --context-json /absolute/path/walmart_context.json \
  --feature-max-chars 280 \
  --output /absolute/path/walmart_audit.json
```

必须读取 audit JSON：

- `release_status = PASS`：可以交付。
- `release_status = REWRITE`：只重写失败模块，再 audit。
- 最多重写 3 次。
- 仍失败时，停止并报告 `BLOCKED`。

## Walmart 输出格式

最终 Listing body：

```text
Product Title:
[one title per size]

Description:
[80-150 word single English paragraph]

Key Features:
[3-10 plain lines]
```

不要在 Listing body 中放：

- 分数
- 审核说明
- Markdown 加粗
- HTML
- emoji
- URL
- 删除记录
- 字符数
