## Recommendation
Prioritize **ISS-usability** (Liked songs deleted and poor recommendations) for the next quarter. It ranks #1 on priority score at 33805 [C-usability-priority_score].

## Why (supporting numbers)
- Complaint count: 11680 [C-usability-complaint_count], second only to ISS-other at 11864 [C-other-complaint_count].
- Severity sum: 33805 [C-usability-severity_sum] vs 23178 for ISS-other [C-other-severity_sum], 18494 for playback [C-playback-severity_sum] and 17713 for billing [C-billing-severity_sum].
- Mean severity: 2.894264 [C-usability-mean_severity], higher than ISS-other at 1.953641 [C-other-mean_severity], so the lead is not driven by volume alone.
- Evidence themes: liked songs and playlists vanishing without explanation, and recommendations ignoring user selections or disabled settings.

## Alternatives considered
- **ISS-other (security, trust, data)**: high volume (11864 [C-other-complaint_count]) but low mean severity (1.953641 [C-other-mean_severity]); the theme is diffuse.
- **ISS-playback (mobile data usage)**: highest mean severity among the large issues at 3.427354 [C-playback-mean_severity] but only 5396 complaints [C-playback-complaint_count]; a strong second candidate.
- **ISS-billing (unwanted charges)**: 6370 complaints [C-billing-complaint_count], priority 17713 [C-billing-priority_score]; the reviews describe financial harm, so it merits monitoring and possibly a parallel fix.
- **ISS-access (hacked accounts)**: mean severity 3.927206 [C-access-mean_severity], but only 1360 complaints [C-access-complaint_count].
- Catalog, downloads and support rank lower (priority 5197 [C-catalog-priority_score], 3106 [C-downloads-priority_score], 263 [C-support-priority_score]).

## Representative reviews (IDs)
- f2c11a77-9616-4d3c-9ea9-85895f42ea7c (liked songs deleted)
- 67753988-a6ac-4582-8f72-62bf0af58adc (paid for years, liked songs deleted)
- 1b72a43a-0608-4b73-991a-b9fbe84a5ebc (lost liked songs)
- e6b6cbef-e961-47f3-8a05-ff74e752f2ad (playlists lost after logout)
- 578e4e04-2a8d-48db-99dd-8bb34291ba21 (random songs despite setting off)

## Limitations
- Priority score equals severity sum, so it favors volume; it is not a measure of revenue or churn impact.
- Cancellation language is stated intent, not observed churn.
- Causes of the deletions are not established by this data.
- The evidence pack contains only a few quotes per issue.
- The ISS-other bucket is broad and may mix distinct problems.
- The run quarantined 560622 rows [run_counts] and 12532 needed review, so the ranking covers only a classified subset.
