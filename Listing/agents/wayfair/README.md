# Wayfair Listing Generator

This directory is the GitHub-hosted AGENTS version of the former local Codex skill `wayfair-listing-generator`.

## Use

From the repository root, read:

```text
AGENTS.md
agents/wayfair/AGENTS.md
agents/wayfair/references/rules.md
```

Then run the helper script:

```bash
python agents/wayfair/scripts/wayfair_kb.py status
```

For a product input file:

```bash
python agents/wayfair/scripts/wayfair_kb.py prepare \
  --text-file /absolute/path/current_product.txt \
  --brand "BRAND_OR_SUPPLIER_NAME" \
  --top 120 \
  --output /absolute/path/wayfair_context.json
```

After drafting the listing JSON:

```bash
python agents/wayfair/scripts/wayfair_kb.py audit \
  --listing-json /absolute/path/draft.json \
  --context-json /absolute/path/wayfair_context.json \
  --output /absolute/path/wayfair_audit.json
```

Only release final copy when the audit returns `release_status: PASS`.

## Included Resources

```text
AGENTS.md
references/rules.md
scripts/wayfair_kb.py
assets/wayfair_listing_knowledge_base.xlsx
```

The workbook is intentionally included so the generator does not depend on any local-only skill installation path.
