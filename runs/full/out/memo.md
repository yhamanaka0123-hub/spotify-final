## Recommendation

Prioritize **ISS-usability (Intrusive ads and cluttered interface)** next quarter. It ranks #1 on priority score (33,805 [C-usability-priority_score]), ahead of ISS-other (23,178 [C-other-priority_score]) and ISS-playback (18,494 [C-playback-priority_score]).

## Why (supporting numbers)

- Usability has 11,680 complaints [C-usability-complaint_count] and a severity sum of 33,805 [C-usability-severity_sum], with mean severity 2.894264 [C-usability-mean_severity].
- Issue profile (computed over all members): ads are mentioned in 5,276 of 11,680 members, shuffle in 1,218, playlist in 2,138, update in 1,830. Severity 3 (degraded but usable) dominates with 8,368 members. Cancellation intent: 913 members (stated intent, not observed churn).
- ISS-other has slightly more complaints (11,864 [C-other-complaint_count]) but low mean severity (1.953641 [C-other-mean_severity]) and is generic dissatisfaction, so it is not actionable as a single workstream.
- Evidence themes: ads for Premium users and frequent ads, update-driven layout changes, and shuffle/queue trouble.

## Alternatives considered

- **ISS-playback**: highest severity among the large issues (mean 3.427354 [C-playback-mean_severity]) with 5,396 complaints [C-playback-complaint_count]. It is the strongest second priority, since many reviews describe a core task being blocked (crashes, stopping). Profile: 2,691 members at severity 4.
- **ISS-billing (free tier locked behind Premium)**: 6,370 complaints [C-billing-complaint_count], priority 17,713 [C-billing-priority_score]. Overlaps with ads and monetization, so it is partly a product/business-model decision. Profile cancellation intent is 977 members.
- **ISS-access**: small volume (1,360 [C-access-complaint_count]) but the highest mean severity (3.927206 [C-access-mean_severity]); login failures block use entirely. This is a good targeted fix candidate despite its lower rank (priority 5,341 [C-access-priority_score]).
- Catalog, downloads, and support rank lower (support: 98 complaints [C-support-complaint_count]).

## Representative reviews (IDs)

- Usability: 77239751-6d0b-4cf5-b257-dc0cb3189f01 (ads in podcasts for a Premium user), e7f02fbb-798f-4b9a-944e-78024741a031 (cannot shuffle after update), 8fc9a390-71cc-4bbd-9a17-cb16b53afeb3 (cannot queue; cancellation intent).
- Playback: b75f0bf4-e31e-43f2-b2c8-e257275af9d3, 47bc8218-5a9c-4cf2-8337-cf09383c3e21.
- Access: 407f1d76-79c7-4f7a-a017-846cf9244b62.

## Limitations

- Run coverage: 100,000 reviews completed; 560,609 rows were quarantined as not_classified_outside_budget_scope (never classified, not failures) and 13 as empty_review_text. 12,532 were flagged needs_review (run_counts).
- Priority score equals severity sum, so it favors volume; it does not measure revenue or churn impact.
- Evidence quotes are a random sample; ISS-usability and ISS-billing overlap on ads and Premium themes, and classification is single-label.
- Cancellation language is stated intent only.
