Log a research note to the journal for a position. If no SYMBOL is provided, ask the user.

## Steps

1. **Confirm SYMBOL** — if not provided as argument, ask which position this note is for.

2. **Ask for note type** — choose one:
   - `earnings` — post-earnings key takeaways
   - `dcf` — DCF / valuation update
   - `comps` — comparable companies analysis
   - `note` — general research note

3. **Ask for content** — have the user provide the note text. Encourage concise, data-rich notes (e.g., "Q4 FY2026 revenue $44.9B, +12% YoY, beat by 3%; guidance $45–47B vs consensus $46.2B; management cited supply constraint on Blackwell").

4. **Write to journal**:
```
/c/Users/zhaix/miniconda3/envs/work/python.exe run.py journal research \
  --symbol {SYMBOL} \
  --type {type} \
  --content "{content}"
```

5. **Confirm** — report success, then note: "The 3 most recent research notes for this symbol will be automatically injected into:
   - `/researcher:analyze {SYMBOL}` or `analyze asset {SYMBOL}` — single-position deep-dive
   - `analyze suggest` — portfolio-wide recommendations (notes for all covered positions are injected)"

## Tips

- One note per event. Don't aggregate multiple events into one entry.
- Include specific numbers. Vague notes ("beat expectations") are useless later.
- If this note should trigger a thesis update, run `/researcher:update {SYMBOL}` next.
