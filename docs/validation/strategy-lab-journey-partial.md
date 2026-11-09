# Strategy-lab journey (partial)

On 9 November 2026, source commit `8ba45ae12aa5ccfeb68aca9c833db158cadc4e45`
was exercised on Windows with Firefox 157.0 at 1440 × 900. Run
`node scripts/preview-demo.mjs` and open `http://127.0.0.1:4173/`.

1. Open **Strategy lab**. Retain the default synthetic assumptions: 30 MW
   capacity, one-hour interval, day-ahead 420, up-regulation 610 and
   down-regulation 310 DKK/MWh. Enter production scenarios `3, 7, 11` MW;
   leave probabilities blank for equal weights. Calculate: the browser
   showed a 7.00 MW offer and 2,540.00 DKK expected interval revenue.
2. Save the case as **Fictional case**. After a reload, the editable draft
   returned to its default scenarios `2, 5, 9, 13, 18, 24, 28` and the
   default offer was 9.00 MW, while the saved case remained in this browser's
   storage. Select **Load** for the saved case: the `3, 7, 11` inputs,
   7.00 MW offer and 2,540.00 DKK expected revenue returned. Browser storage
   is local and can be cleared; the interface offers JSON export for backup.
3. With the project installed, the equivalent Python call below returned
   `offer_mw: 7.0` and `expected_revenue_dkk: 2540.0`:

   ```python
   from zephyrtrade.app import optimize_payload
   optimize_payload({"capacity": 30, "hours": 1, "da": 420, "up": 610,
                     "down": 310, "scenarios": [3, 7, 11],
                     "probabilities": [1/3, 1/3, 1/3]})
   ```

Separately, `python scripts/verify_engines.py` passed 120 cases generated with
seed 42; its maximum Python/browser objective difference was
`2.3283064365386963e-10` DKK, below its `1e-6` DKK tolerance. The script
generates cases and does **not** read or replay a run manifest. This note
therefore does not claim the manifest-replay journey requested in the issue.
No trades were placed. The values are hypothetical research inputs and results.
