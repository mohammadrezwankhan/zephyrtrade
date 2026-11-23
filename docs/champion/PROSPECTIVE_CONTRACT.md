# Prospective information-vintage controls — not a G2 approval

This is a **synthetic, invented** fixture and a separately labelled **control** for unit-testing decision-time data availability. It is not an exchange rule, production configuration, verified archived weather forecast, prospective-model backtest, or trading proposal. The original Phase 1–3 retrospective data, masks, weights, prices, economics and published metrics are unchanged.

The module in src/zephyrtrade/issuance_contract.py uses a **hypothetical** Europe/Copenhagen previous-local-day **12:00** deadline. DST is handled by finding the prior *local calendar date* before converting noon to UTC, avoiding the incorrect assumption that a local day always lasts exactly 24 hours. It rejects naive timestamps, missing/duplicate UTC delivery hours, missing or ambiguous eligible issue-time vintages, and forecasts only available after the hypothetical gate. Future forecast revisions cannot alter a past selected vintage. The illustrative offer is simply the selected issued-power forecast clipped to capacity; *realised production, weather and market prices are not used to choose it*. This is not a replacement for the Phase 2/3 learners.

The versioned tests/fixtures/issued_power_v1.json is explicitly **invented** and includes a deliberately late issue after the hypothetical gate. The adversarial tests cover DST, late-vintage mutation, gaps/duplicates, contradictory availability timestamps, naive dates, and clipping. This proves the small toy implementation's information-access boundary only; it does **not** prove archived meteorological forecasts were actually issued on time.

The test in tests/test_matched_mask_sensitivity.py independently demonstrates with four invented settlement intervals that the **same evaluation hours for both strategies** can reverse their ranking when negative-price hours are dropped: one strategy leads on the retained population, the other on all hours. It does not reconstruct the archived 53 missing historical intervals. Both samples use the same offer vectors, settlement equation and prices; neither result may be presented as a population-estimated prospective advantage.

## Source-backed 23 November shadow record

A separate, one-day record now exercises a real pre-gate information set without relabeling the synthetic Phase 1–3 study. Nord Pool's day-ahead specification sets gate closure at 12:00 CET on D−1; for this winter-date observation that is **2026-11-22 11:00 UTC**. The replay uses only the single ECMWF IFS run initialized at 00:00 UTC and weather response observed at 07:59 UTC (minute precision), plus the Nord Pool 22 November version-2 price response observed at 07:59:25.819862 UTC. The latter is copied to the same local quarter-hour on 23 November; it is a **previous-day price-persistence feature**, not an exchange-issued price forecast. Both information sources precede the recorded gate. [Nord Pool day-ahead gate](https://www.nordpoolgroup.com/en/the-power-market/Day-ahead-market/) · [Pre-gate input receipt](https://github.com/mohammadrezwankhan/voltrl/issues/42#issuecomment-7076242486).

The 23 November schedule was observed at 08:01:20 UTC, before the gate. Its 96 quarter-hour positions are reconstructed from the captured 100 m wind forecast, previous-day DK2 price features, and the repository's generic 3/12/25 m/s power curve with 30 MW capacity, 0.94 wake efficiency, and assumed availability 1. The archived schedule SHA-256 is recorded in [the versioned evidence manifest](evidence/ronne-20261123-v1.json). This is a deterministic educational proxy schedule; it is not a real plant, accepted market order, or forecast-volume measurement.

The later Nord Pool auction version 2 was updated at 12:12:36.5130211 UTC and observed at 12:38:01.069269 UTC, after the gate. The replay reads it only after freezing the schedule. It scores the same-local-quarter-hour price-persistence forecast and a prior-day-area-mean price baseline on a common UTC mask. The run reports 96/96 matched intervals. It is a **one-day price-only out-of-sample score**, not a backtest of the ZephyrTrade offer learners, turbine output, imbalance settlement, or farm revenue. The schedule-volume mark at clearing prices is a counterfactual quantity-price calculation only. [Post-gate outcome receipt](https://github.com/mohammadrezwankhan/voltrl/issues/42#issuecomment-7079283975).

To replay the archived local files without network access:

```bash
python scripts/replay_prospective_record.py \
  --weather-snapshot ../market-vintage-snapshot-20261122.json \
  --price-input-csv ../volt-20261123-forward.csv \
  --price-source-response-json ../volt-20261122-as-received.json \
  --price-observation-receipt-json ../volt-20261122-observation.json \
  --auction-outcome-json ../volt-20261123-auction-as-received.json \
  --auction-observation-receipt-json ../20261123-forward-price-score.json
```

The script verifies the raw source files, observation receipts, their recorded timestamps and hashes, and every derived CSV value against the raw price response. The manifest must use the standard noon gate on the previous Copenhagen calendar day, with the UTC offset for that date. A postponed auction would need its own source-backed cutoff and replay support. The schedule timestamp must follow the recorded input observation bounds, and the auction receipt cannot predate its source version. It emits compact score JSON to stdout. Raw Nord Pool price rows are not vendored because redistribution rights are not established. The receipts are at [VoltRL issue #42](https://github.com/mohammadrezwankhan/voltrl/issues/42); the replay requires locally archived files whose hashes match the manifest. The Open-Meteo weather data are attributed under [CC BY 4.0](https://open-meteo.com/en/license).

**Still blocked:** [#92](https://github.com/mohammadrezwankhan/zephyrtrade/issues/92) requires source-authentic vintages for the retained historical model inputs, a causal evaluation of the original model family on an actual matched outcome population, relevant negative-price coverage, and independent scientific challenge/sign-off. A real pre-gate weather run and one-day price-persistence score do not establish those missing historical or farm-level claims. Human UAT has not been completed. The champion/prospective status remains **not verified**, even if all automated tests on this branch pass. No merge or deployment is authorized by this supplemental record.
