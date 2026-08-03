# Trade Record

## Goal

Record an externally executed transaction and update structured portfolio state.

## Preconditions

- An approved decision reference exists and its document is marked
  `**Status:** approved`, unless this is a baseline import or explicit correction.
- Execution evidence states a stable execution reference, symbol, side,
  quantity, price, fees, currency and time.

## Steps

1. Verify execution evidence against the decision boundary.
2. Record the trade through `PortfolioStore.record_trade`, passing both
   `decision_ref` and `execution_ref`; it updates the
   position, settlement cash and event log in one transaction.
3. Record deposits/withdrawals separately as cashflows. Do not record trade
   proceeds a second time. Use the option transition methods for option events.
4. Generate a fresh portfolio state and data-quality report.
5. Append an execution note linked to the decision and generated event ID.

Do not rewrite the thesis merely because a trade occurred.
