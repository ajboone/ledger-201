# Monthly intelligence smoke test — October 5, 2026

Executed all seven requested questions against the running local
`POST /api/ai-analyst/query`, location 1, using the actual imported September
2026 report. Each request supplied user context identifying September 2026;
there was no inferred year. These were live provider calls, separate from the
automated test suite, which uses fake responses only. No stored report rows
were changed. This verified API answers and tool traces, not browser rendering.

| Question | Observed tool and result |
| --- | --- |
| Best selling items? | Revenue and quantity tools; Teriyaki Chicken led revenue ($2,386.40), Fountain Soda led units (348). No standalone Regular item. |
| Most by volume? | Quantity tool; Fountain Soda 348, Tea 326, Downtown roll 202. |
| Most revenue? | Revenue tool; Teriyaki Chicken, Hibachi Steak, Downtown roll, Dynamite Roll, SC Roll. |
| Kitchen versus sushi? | Routing mix; kitchen $21,608.90 (45.68%), sushi $18,612.72 (39.35%), both printers $7,079.09 (14.97%). Explicitly called production routing, not menu departments or profitability. |
| Best menu categories? | Category breakdown; Beverages & Extra Sauces led ($1,252.78). Routing groups excluded, with the limitation explained. |
| Sales concentration? | Concentration tool; top five $8,620.10 / $53,551.74 = 16.10%, with item-detail caveat. Separate endpoint check: top ten $14,082.35 = 26.30%. |
| Highest margin? | Explained that item-level cost data is missing; did not invent margin or substitute sales per unit. |

## Source ambiguity retained

The older local import stored flattened quantity markers in labels (`Regular ×`,
`Kitchen Print ×`) and repeated parent/variation rows. The read-time view now
cleans those markers and folds supported repeated variations.

`Custom Amount` and `No description` each show 86 units and $626.82, immediately
adjacent. The stored data lacks indentation or repeated-label evidence to prove
that the latter is a variation. They remain separate with a warning. The
normalized detail sum is $54,178.56, versus the report's $53,551.74 Items total:
the $626.82 discrepancy is consistent with one duplicated row, but that alone
does not establish the parent/child relationship. Inspect the original layout
before any manual correction. Top-five and top-ten results do not include
either of these rows, but remain qualified by the detail-quality warning.

## Presentation observation

Several live answers use Markdown tables. The existing frontend uses plain
CommonMark rendering without a GFM table plugin, so table rendering merits a
separate UX check. No frontend files or answer-formatting prompts were changed
as part of this monthly-analysis task.
