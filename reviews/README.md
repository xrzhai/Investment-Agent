# Private Reviews

This ignored directory contains the human-readable audit trail around the
structured portfolio ledger.

Recommended layout:

```text
reviews/
  portfolio/YYYY/YYYY-MM-DD.md
  decisions/YYYY/YYYY-MM-DD_SYMBOL.md
  executions/YYYY/YYYY-MM-DD_SYMBOL.md
  postmortems/YYYY/YYYY-MM-DD_slug.md
```

- Portfolio reviews use `templates/portfolio/review.md`.
- A decision record must exist before a normal trade is recorded.
- Execution records cite broker evidence and the decision record.
- Review files are private and are not loaded by research-only tasks.
- This repository tracks only this README; local review history stays ignored.
