# Wayfair Listing Generator AGENTS

Use this file for Wayfair / 威菲尔 rug listing generation and audit. This is the GitHub-hosted AGENTS version of the former local `wayfair-listing-generator` skill.

Do not apply Amazon, Walmart, CDQ, Search Terms, Item Highlights, or brand-first title rules to Wayfair output. The bundled workbook is the source of truth for Wayfair rules, Pattern, Color, Decorative Additions, and keyword-library terms.

## Required Workflow

1. Collect only the current product image facts and current user attributes.
2. Create a UTF-8 text file with the current product facts, requested claims, image notes, sizes, and brand/supplier name. Brand/supplier is used only for exclusion.
3. Run `prepare` from the repository root:

```bash
python agents/wayfair/scripts/wayfair_kb.py prepare \
  --text-file /absolute/path/current_product.txt \
  --brand "BRAND_OR_SUPPLIER_NAME" \
  --top 120 \
  --output /absolute/path/wayfair_context.json
```

4. Read the JSON fully. Confirm:
   - `knowledge_status.ready` is `true`;
   - `input_scan.pass` is `true`;
   - selected Pattern and Colors match the current product/image;
   - `machine_washable` and `non_slip_backing` are confirmed, because both are fixed title terms.
5. Read `agents/wayfair/references/rules.md` before drafting.
6. Draft internal audit JSON:

```json
{
  "titles": [
    {"slot": "Title1", "type": "Doormat", "title": "..."},
    {"slot": "Title2", "type": "Hallway Runner", "title": "..."},
    {"slot": "Title3", "type": "Area Rug", "title": "..."}
  ],
  "marketing_copy": "...",
  "feature_bullets": ["...", "...", "...", "...", "...", "..."]
}
```

7. Run audit:

```bash
python agents/wayfair/scripts/wayfair_kb.py audit \
  --listing-json /absolute/path/draft.json \
  --context-json /absolute/path/wayfair_context.json \
  --output /absolute/path/wayfair_audit.json
```

8. If audit returns `REWRITE`, rewrite only failed modules and rerun. Release final copy only when `release_status` is `PASS`.

## Fixed Final Output Format

Return only these sections, in this order:

```text
Title1:
[Doormat title]

Title2:
[Hallway Runner title]

Title3:
[Area Rug title]

Marketing Copy:
[one 5-sentence paragraph following the fixed operator structure]

Feature Bullets:
[6 plain lines; lines 1, 2, 4, 5, and 6 must use the fixed operator copy; line 3 changes by image]

Keyword / Attribute Usage Summary: Pattern&Colors
Pattern: [one workbook Pattern]
Colors: [one to three workbook Colors]
Title Type Mapping: Title1=Doormat; Title2=Hallway Runner; Title3=Area Rug
Keywords Used: [safe relevant keywords]

Blocked Input / Risk Screening:
[category-level handling]

Wayfair Audit:
[PASS/REWRITE and compact metrics]
```

Do not output `Product Titles`, `Needs manual confirmation`, tables, HTML, or extra sections.

## Title Rules

Always generate exactly three titles:

- `Title1` = Doormat title.
- `Title2` = Hallway Runner title.
- `Title3` = Area Rug title.

Each title must follow this exact structure:

```text
Machine Washable + Pattern + Color + Product Type + With Non-Slip Backing
```

Hard title gates:

- The title must start with `Machine Washable`.
- The title must end exactly with `With Non-Slip Backing`.
- No word, scenario, punctuation, size, or extra phrase may appear after `With Non-Slip Backing`.
- Title text itself must contain its product type: `Doormat`, `Hallway Runner`, or `Area Rug`.
- Pattern is one workbook Pattern, chosen from image/product evidence. Motif modifiers may be used before the workbook Pattern when needed for accuracy, such as `Zebra Animal Print`, while the summary Pattern remains `Animal Print`.
- Color uses one to three workbook Colors, separated with ` / `.
- Title must be at least 80 English characters when safe. If the exact framework cannot reach 80 without inaccurate terms, do not append words after the fixed tail; expand only the Pattern/Color segment with supported motif or color modifiers.
- Put high-traffic words in the first 60-70 characters when possible.
- Do not include brand/supplier names, shipping promises, warranty/guarantee wording, ranking claims, price/promotion language, URLs, HTML, emojis, all-caps names, controversial content, or keyword stuffing.
- Do not use inaccurate colors, sizes, materials, gender, youth, kids, or nursery terms.
- Use Title Case; short prepositions/articles/conjunctions may stay lowercase.

## Marketing Copy Rules

Marketing Copy must follow the operator-provided 5-sentence structure. Do not treat the Feature Bullets sample as a Marketing Copy template.

Sentence 1 is image-based and must change by product:

- State product style, workbook Pattern, workbook Colors, and the design inspiration source, such as art history, textile tradition, garden forms, nature, safari markings, vintage design, or modern graphic art.
- Use sensory, visual language that gives the shopper a clear picture.
- Describe the visual layout from the inside outward: first the central or dominant visual focus, then the surrounding field, frame, border, or edge treatment. If the rug has no border, describe how the motif moves across the field toward the edges.

Sentences 2-4 cover core selling points and high-frequency scenes:

- Sentence 2: faux cashmere surface tactile experience, including durable and soft/velvety comfort.
- Sentence 3: machine washable convenience plus bedroom and living room scenes.
- Sentence 4: sponge interlayer non-slip backing construction.

Sentence 5 is fixed trust and safety copy and must be output exactly:

```text
This rug is ensuring its materials don't contain harmful substances.
```

Other Marketing Copy gates:

- One English paragraph.
- Exactly 5 sentences.
- Target 75-100 words.
- Do not mention supplier or brand names.
- Do not include option-specific size, finish, or fabric details when copy is shared across variants.
- Use active voice, friendly conversational tone, and one idea per sentence.
- Avoid keyword stuffing, generic statements, empty descriptors, technical jargon, and repeated bullet/spec wording.
- TPR may be mentioned only when the current product input explicitly confirms TPR backing. Otherwise use `non-slip backing` or `sponge interlayer non-slip backing`.

## Feature Bullet Rules

- Generate exactly 6 bullet lines.
- Lines 1, 2, 4, 5, and 6 are fixed operator copy and must be output exactly as written below.
- Only line 3 changes by current image/product visual facts.
- Line 3 should describe the current Pattern, Colors, motif, and style.
- Do not add punctuation at the end of any bullet line.
- Do not rewrite, shorten, translate, or localize the fixed lines.

Fixed Feature Bullets:

```text
Premium spill-resistant faux cashmere surface prevents liquids and pet accidents from penetrating the fibers
The non-slip backing with a sponge interlayer ensures the rug stays firmly in place on the floor, eliminating the need for a separate non-slip pad
[Image-based visual design line]
Machine washable construction allows for a quick refresh to handle real-life household messes
Soft low-pile surface resists shedding and daily wear while remaining gentle on feet and paws
This area rug is ideal for various settings such as the living room, bedroom, dining room, kitchen, and other high-traffic areas
```

For line 3, follow this structure:

```text
[Current motif/pattern] in [current colors] adds [current style or design effect] to any interior space
```

Examples:

- `Charming floral and bow motif in soft pastels adds a romantic vintage touch to any interior space`
- `Zebra animal print in gray cream and ivory adds a modern safari touch to any interior space`

Legacy constraints that still apply:

- Each bullet should be 5-30 words.
- Do not end bullets with punctuation.
- Do not repeat Marketing Copy verbatim.

## Evidence And Risk Rules

- User-provided words are not exempt from scanning.
- Treat requested claims as current evidence only after risk screening.
- TPR is not a default Wayfair wording rule. Use it only as a current product fact; otherwise use the safer fixed wording `non-slip backing`.
- Feature Bullet lines 1, 2, 4, 5, and 6 are operator-provided fixed copy. Their fixed wording is audited for exact match and is not regenerated from current input. Do not carry their fixed claims into Marketing Copy unless the current input also supports them.
- Marketing Copy has its own operator-provided fixed structure. The fixed Marketing Copy elements `faux cashmere surface`, `sponge interlayer`, and `don't contain harmful substances` are audited as required operator copy.
- Reword absolute claims into safer claims when needed, such as `helps reduce` rather than `prevents`.
- Do not echo raw blocked terms in the user-facing output unless debugging is explicitly requested.

## Bundled Resources

- `agents/wayfair/assets/wayfair_listing_knowledge_base.xlsx`: complete workbook with title rules, Marketing Copy logic, Feature Bullets sample logic, Pattern, Color, Decorative Additions, and keyword Impressions.
- `agents/wayfair/references/rules.md`: compact production rules.
- `agents/wayfair/scripts/wayfair_kb.py`: workbook loader, scanner, keyword/context retriever, and final audit.
