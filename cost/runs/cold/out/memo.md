## Recommendation
Prioritize **ISS-usability** (Frequent ads and restrictive skip limits) for the next quarter. It ranks first on the saved priority score.

## Why (supporting numbers)
- 17 complaints [C-usability-complaint_count], the highest of any issue.
- Severity sum of 48 [C-usability-severity_sum] and priority score of 48 [C-usability-priority_score], versus 28 [C-other-priority_score] for the next-ranked issue (general dissatisfaction, which is vague).
- Mean severity is 2.823529 [C-usability-mean_severity]: a degraded or restricted function, not a blocked core task.
- Reviews cite ads every one or two songs, a six-skip limit, and being unable to repeat or play a specific part.
- Some reviews state intent to leave (stated intent only, not observed churn).

## Alternatives considered
- **ISS-other**: 13 complaints [C-other-complaint_count], priority 28 [C-other-priority_score]. Mostly vague, so it is not actionable.
- **ISS-playback**: 5 complaints [C-playback-complaint_count], but the highest mean severity among the larger issues at 3.600000 [C-playback-mean_severity]. Crashes and a stuck loading screen block core use. Priority score is 18 [C-playback-priority_score]. Strong candidate for a parallel reliability fix.
- **ISS-billing** (Premium paywall): 6 complaints [C-billing-complaint_count], priority 17 [C-billing-priority_score]. It overlaps heavily with usability, since the skip-limit complaints appear in both.
- **ISS-access**: only 2 complaints [C-access-complaint_count], but mean severity 4.000000 [C-access-mean_severity]. Small sample.
- Catalog (priority 15 [C-catalog-priority_score]) and downloads (priority 7 [C-downloads-priority_score]) rank lower.

## Representative reviews (IDs)
- ebc64fe2-9553-4528-87d5-cb4bb9783be6 (skip limit)
- 3e8bdc92-4934-457e-85cc-8b9d14bf51c0 (ads every 1 or 2 songs)
- e16a4550-43e7-4ae1-b538-a65cc652c31b (stated intent to leave, cannot repeat or play a specific part)
- 035213ba-b1b9-411c-b028-70296e5f0e73 (stated intent to uninstall, ads)
- Playback: 55cc3abf-c295-4591-8c3a-78085cfdefaa (crash after update)

## Limitations
- The sample is small, 100 source rows, so counts are indicative only.
- 3 rows were flagged as needing review.
- The priority score is severity-weighted volume. It does not measure revenue, churn or causes.
- Cancellation language is stated intent, not observed churn.
- Usability and billing complaints overlap thematically, and many reviews tie the changes to a recent update.
