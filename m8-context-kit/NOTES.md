# m8 context-kit notes

- `must_keep` survives three compactions: `test_context.py` and agentkit's `test_decision_survives_three_compactions`.
- `experiment.py --dry-run`, 60 turns: naive append averaged 11,651 input tokens per call, compaction 1,212 (9 summary calls), structured state 90. Accuracy needs a live run.
- Failure mode per fix: compaction targets context rot and cost; `must_keep` targets lost decisions; structured state targets distraction; the repair loop targets repeated code errors.
