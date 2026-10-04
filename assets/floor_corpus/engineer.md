Switched note systems last month. Results below.

Previous setup: nested folders, four levels deep. Filing latency averaged 20-30 seconds per note. Retrieval required remembering the taxonomy. Failure mode: notes filed under plausible-but-wrong categories were effectively lost.

New setup: flat namespace, full-text search, backlinks. Filing latency: zero. Retrieval: search by any remembered fragment. Tested against 400 legacy notes migrated without reorganization.

Measured outcomes after 30 days:
- Notes captured per week: 41 vs. 12 under old system.
- Median retrieval time: 4 seconds vs. 25 seconds.
- Notes lost (unretrievable when needed): 0 vs. approximately 2 per week.

The folder system optimized for a browsing pattern that never occurred. Access logs confirmed 96% of retrievals started with search, not navigation. Maintaining a hierarchy to serve 4% of lookups was a poor trade.

Remaining issues: search recall degrades on notes under 10 words. Mitigation: enforce minimum context per note. Will re-evaluate at 90 days. Recommendation: skip folder taxonomies entirely for personal knowledge bases under 10k documents.
