# Wayfair Listing Production Rules

## Output Order

Return exactly:

```text
Title1:
Title2:
Title3:
Marketing Copy:
Feature Bullets:
Keyword / Attribute Usage Summary: Pattern&Colors
Blocked Input / Risk Screening:
Wayfair Audit:
```

## Title Rules

- `Title1` is the Doormat title.
- `Title2` is the Hallway Runner title.
- `Title3` is the Area Rug title.
- Exact title structure:
  `Machine Washable + Pattern + Color + Product Type + With Non-Slip Backing`
- `With Non-Slip Backing` is the final text. Nothing can come after it.
- Product type must be visible in the title text itself.
- Pattern is single-select from workbook Pattern.
- Colors are one to three workbook Colors joined by ` / `.
- Title must be at least 80 characters when possible without violating the
  exact tail rule.
- If title is short, lengthen only inside Pattern/Color using supported visual
  facts, for example motif + workbook Pattern. Never append scenario words
  after `With Non-Slip Backing`.
- Do not include supplier/brand names, price/promo language,
  shipping promises, warranty/guarantee claims, all-caps names, controversial
  terms, URLs, HTML, emojis, or keyword stuffing.

## Title Type Intent

- Doormat: entryway, doorway, front door, kitchen sink, mudroom, low-door or
  small mat placement. Do not append this intent after the fixed tail.
- Hallway Runner: hallway, corridor, laundry, kitchen path, or long narrow
  runner placement. Do not append this intent after the fixed tail.
- Area Rug: living room, bedroom, dining room, office, nursery, sitting room,
  or broad room-size placement. Do not append this intent after the fixed tail.

## Marketing Copy Logic

Use the operator-provided 5-sentence structure, not a generic product
description:

1. Sentence 1 is image-based. It states product style, Pattern, Colors, and
   design inspiration such as art history, textile tradition, garden forms,
   nature, safari markings, vintage design, or modern graphic art. It must give
   the shopper a clear picture by describing the visual layout from the inside
   outward: central/dominant visual focus first, then surrounding field, frame,
   border, or edge treatment. If there is no border, describe how the motif
   moves across the field toward the edges.
2. Sentence 2 covers faux cashmere surface touch, durable use, and soft or
   velvety comfort.
3. Sentence 3 covers machine washable convenience and placement in bedrooms and
   living rooms.
4. Sentence 4 covers sponge interlayer non-slip backing construction.
5. Sentence 5 is fixed and must be output exactly:
   `This rug is ensuring its materials don't contain harmful substances.`

Rules:

- One English paragraph.
- Exactly 5 sentences.
- Target 75-100 words.
- Do not mention supplier/brand names.
- Do not include option-specific size, finish, or fabric details in shared copy.
- Friendly active voice, one idea per sentence.
- No keyword stuffing, generic filler, repeated bullets/specs, or unsupported
  language.
- The workbook sample under Feature Bullets is not a Marketing Copy template;
  use it only for bullet logic.
- TPR may be mentioned only when the current input confirms TPR backing.

## Feature Bullets

- Exactly 6 bullet lines.
- Lines 1, 2, 4, 5, and 6 are fixed operator copy. Output them exactly:

```text
Premium spill-resistant faux cashmere surface prevents liquids and pet accidents from penetrating the fibers
The non-slip backing with a sponge interlayer ensures the rug stays firmly in place on the floor, eliminating the need for a separate non-slip pad
[Image-based visual design line]
Machine washable construction allows for a quick refresh to handle real-life household messes
Soft low-pile surface resists shedding and daily wear while remaining gentle on feet and paws
This area rug is ideal for various settings such as the living room, bedroom, dining room, kitchen, and other high-traffic areas
```

- Only line 3 changes by current image/product facts.
- Line 3 must describe Pattern, Colors, motif, and style.
- Recommended line 3 structure:
  `[Current motif/pattern] in [current colors] adds [current style or design effect] to any interior space`
- No punctuation at the end of any bullet line.
- Do not carry fixed-bullet claims into Marketing Copy unless current evidence
  independently supports them.

## Keyword And Attribute Rules

- Use only relevant terms from the bundled keyword library.
- Prefer keyword-library terms that match the current product type, Pattern,
  Colors, use scene, and supported attributes.
- Pattern and Colors in summary must match the final titles.
- Use current image/text to override weak workbook candidates when necessary.
- Use kids/nursery/outdoor/material terms only with current evidence.

## Release Gate

Release only when:

- workbook is ready;
- input and final output risk scans pass;
- Title1/Title2/Title3 are present and mapped correctly;
- each title starts with `Machine Washable`;
- each title ends exactly with `With Non-Slip Backing`;
- no title has words after the fixed tail;
- Marketing Copy is one paragraph and follows the 5-sentence operator logic;
- Feature Bullets pass count, fixed-line exact match, and image-based line 3;
- no brand/supplier terms appear in customer-facing copy.
