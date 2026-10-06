# Analyst synthesis verification - October 5, 2026

## Changes

Monthly instructions now prioritize supported relationships over recaps, compare
revenue and volume with reported sales per unit, use concentration descriptively,
and distinguish observations from next analytical questions. Repeated caveats
should be compact and relevant. Existing provenance and data-boundary rules remain.

Tool selection remains model-driven within the existing bounded loop. Instructions
encourage complementary tools when useful and reuse metrics already present in
ranking results. Descriptions clarify the legacy ranking, cross-metric comparisons,
top-5/top-10 concentration, and discount dollar share versus usage share.

No deterministic financial calculations, schemas, frontend files, or data sources
changed. Discount share is explicitly permitted as a derived comparison of existing
tool-supplied amounts, subject to scope, sign, and nonzero-total checks.

## Automated verification

- `python -m pytest -v`: 209 passed, including nine new test cases.
- `python -m compileall app`: passed.
- `python -m pip check`: no broken requirements found.
- `git diff --check`: passed.

Commands used the repository's existing Windows virtual environment. New tests
exercise multiple tool rounds with actual deterministic payloads: differing
revenue/quantity ranks, per-unit minor-currency values, concentration denominators,
discount amounts, routing shares, history preservation, policy delivery, and
single-tool handling of a narrow monthly fact. Responses API calls are mocked.
Policy assertions do not prove a live model will obey the instructions.

## Illustrative synthesis, not live model output

In the test fixture, Soda leads volume at 20 units but ranks third in revenue at
$10. Steak ranks second in revenue at $20 despite only two units; its reported
sales per unit are $10 versus Soda's $0.50. That explains the ranking contrast
without implying menu price or margin. Military accounts for 95% of the fixture's
reported discount dollars, which does not establish policy effectiveness.

## Manual smoke verification pending

Automatic approval review rejected the live run because it would send imported
September financial report data to the configured external AI provider. No live
calls ran. Explicit approval for that transfer is required to complete these
checks, using September 2026 context and a read-only database connection:

| Exact prompt | Acceptance criteria |
| --- | --- |
| What is interesting from this data? | Prioritized insights, cross-metric comparison, concentration/discount share when useful; no generic recap. |
| What is interesting about the top items? | Compare revenue, volume, and reported sales per unit. |
| What should Jacob pay attention to? | Grounded observations and cautious next questions; no speculative business advice. |
| Which item is most profitable? | Explain that cost data is missing; do not substitute revenue or sales per unit. |
| Is kitchen doing better than sushi? | Compare operational routing shares; distinguish sales from profitability and workload. |

Live answer quality, tool-selection quality, and actual caveat brevity remain
unverified. These changes guide the model; they do not add an output claim validator.
