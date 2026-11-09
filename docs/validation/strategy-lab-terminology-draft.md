# Strategy Lab terminology: draft for review

Automated source review, 9 November 2026, against commit `8ba45ae12aa5ccfeb68aca9c833db158cadc4e45`. A wind-market reviewer, review date, and agreed decisions are pending; this is not expert sign-off.

| Displayed term | Context and review point |
| --- | --- |
| Settlement interval; Day-ahead price; Up-regulation price; Down-regulation price | The [scenario form](https://github.com/mohammadrezwankhan/zephyrtrade/blob/8ba45ae12aa5ccfeb68aca9c833db158cadc4e45/src/zephyrtrade/web/app.js#L384) uses hours and DKK/MWh. Review the wording against the stated settlement assumptions and price ordering. |
| Production scenarios | The same form takes values in MW with optional probabilities. They are editable assumptions, not a live forecast or bid. Review whether this distinction is clear. |
| Expected scenario revenue | The [result](https://github.com/mohammadrezwankhan/zephyrtrade/blob/8ba45ae12aa5ccfeb68aca9c833db158cadc4e45/src/zephyrtrade/web/app.js#L390) shows DKK for the chosen interval and assumptions. Review whether its interval and hypothetical nature are sufficiently visible. |
| Realised revenue; Perfect-foresight capture | The [dashboard](https://github.com/mohammadrezwankhan/zephyrtrade/blob/8ba45ae12aa5ccfeb68aca9c833db158cadc4e45/src/zephyrtrade/web/app.js#L356) shows DKK and percent. The [metric definitions](https://github.com/mohammadrezwankhan/zephyrtrade/blob/8ba45ae12aa5ccfeb68aca9c833db158cadc4e45/src/zephyrtrade/web/app.js#L421) specify the benchmark and settlement formula. Review whether “realised” could imply actual trades in this synthetic application. |
| Offer RMSE; Offer MAE; Imbalance | The [comparison](https://github.com/mohammadrezwankhan/zephyrtrade/blob/8ba45ae12aa5ccfeb68aca9c833db158cadc4e45/src/zephyrtrade/web/app.js#L366) labels offer errors in MW; the metric definitions distinguish offer error from forecast error and calculate imbalance in MWh. Review this power/energy distinction. |

No UI wording was changed. A domain reviewer should record a name and date, and an agreed alternative or “no change” for each row.
