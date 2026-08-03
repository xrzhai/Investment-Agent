# Private Portfolio Data

`investment.db` is the local SQLite fact source for positions, cash, options,
quotes, snapshots and portfolio events. Database files remain ignored.

Do not open the database as Agent context and do not edit it with ad-hoc SQL.
Use `harness.portfolio.PortfolioStore`, back up before schema migration, and use
the bounded state/event queries described in `contracts/retention.md`.
