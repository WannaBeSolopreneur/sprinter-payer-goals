# Hi Sprinter Health team, I built this to show how I would approach your Analytics Engineer role.

This is a private demo of a payer goals page. One fake health plan, Harborline Health Plan, sees progress against a few goals. The numbers come from dbt. The page does not calculate them again.

The data is synthetic. It is not Sprinter data, not a real payer, and not PHI.

Nothing here is deployed. GitHub Pages is not turned on.

## Run

```
make all
```

That creates a virtualenv, generates the seeded feed, runs `dbt build`, and writes `site/data.json` and `site/data.js`. Open `site/index.html`. There is no site build step. Chart.js loads from a CDN.

## What the page says

The quarter is Q4 2026, read on Nov 6, 2026. That is day 37 of 92. A pace goal is on track at 95% of a straight-line pace or better, at risk from 80% up to 95%, and behind below that. A snapshot goal uses those cutoffs against the full target. When a lower number is better, the score flips.

From the latest `make all`:

- Visits completed: 640 of a 1800 quarter goal. 88.4% of pace. At risk. Behind pace by 84 visits.
- Days to a visit: median 8 days against a 7 day target. At risk. Over the target by 1 day.
- Members overdue: 720 against a ceiling of 500. Behind. Over the target by 220 members.
- Visit completion: 78% against an 85% target. At risk. Short of the target by 7 points.

Actions this week, from the same mart:

- 640 in-home visits are completed. The quarter goal is 1800. Behind pace by 84 visits.
- 720 members are overdue for preventive or chronic home care. The target is 500 or fewer. Book the oldest gaps first.
- 48 members had an ER visit within 30 days of a missed home visit this quarter. Call that list this week.
- 65 visits were no-shows this quarter. Completion is 78% against an 85% target. Offer those members a new time.
- 90 referrals are more than 14 days old and still have no visit scheduled. Put them on the schedule this week.

The hero chart is cumulative completed visits against a dashed straight line to the quarter goal. It does not plot a raw week. The line stops on Nov 6. The pace line continues to Dec 31.

## Architecture

`payer_model/generate.py` reads `assumptions/population.yml` and `assumptions/goals.yml`. Seed `20261106`. It writes a DuckDB file.

dbt layers, in order:

1. Staging cleans the raw feed. Duplicate visit rows keep the latest ingest. Status is lower case. A blank visit type is filled from the referral. A referral clock that lands after the visit is pulled back.
2. Intermediate keeps every payer. It adds days from referral to a completed visit, the overdue flag, and the ER-after-miss rule.
3. Marts keep one payer, `payer_harborline`. `mart_goal_status` and `mart_actions_this_week` are the source of the tiles and the action list.

SQL stays on functions Snowflake and DuckDB share. Date math goes through macros in `dbt/macros`.

The Snowflake row access policy is an example in `dbt/analyses/snowflake_row_access_policies.sql`. dbt does not run it on DuckDB. The marts join to `dim_payer`, and the export checks the payer id again before it writes the page file. Northwind Mutual and Cedar Ridge Health stay upstream so the isolation test has rows to drop.

## Metrics

`dbt/models/semantic.yml` is the metric list. The goal mart uses the same facts.

| Metric | Definition |
| --- | --- |
| Visits completed | Completed in-home visits for Harborline from Oct 1 through Nov 6 |
| Median days to a completed visit | Median days from the referral date to the completed visit, in that same window |
| Members overdue | Members with a preventive or chronic gap that is due on or before Nov 6 and is not closed yet |
| Visit completion rate | Completed visits divided by finished visits. Finished means completed, canceled, or no-show. Scheduled visits are not in the rate |
| ER after a missed visit | Members with an ER event 1 to 30 days after a missed home visit in the quarter, and no completed home visit between them |

A lower goal is on track when the value is at or under the target divided by 0.95. Median days and overdue members use that rule. The ER count is an action, not a fifth goal, because it is a utilization hint and not a causal finding.

## Assumptions

Every row is fake. Public figures from the Sprinter job post are context only. The post says Sprinter has served more than 2 million patients, completed more than 130,000 in-home visits, holds a 92 NPS, and works in 22 states. This demo does not use those figures as targets or as page metrics. Harborline is one made-up plan, not the company.

Generation settings in `assumptions/population.yml`:

- Three payers. Harborline has 8,000 members. Northwind Mutual has 3,200. Cedar Ridge Health has 2,600.
- History runs from Nov 7, 2025 through the quarter. The goal window is Q4 2026, Oct 1 to Dec 31. The as-of date is Nov 6, 2026.
- Harborline quarter through Nov 6 is built to a quota: 640 completed visits, 115 canceled, 65 no-shows. The visit durations are built so the median is 8 days.
- 720 members have an open preventive or chronic gap. 150 other gaps close when a completed preventive visit lands in October.
- 48 members get an ER event 5 to 12 days after a missed visit in the first part of the quarter, so the ER date still falls on or before Nov 6.
- 90 referrals are 20 days old and have no visit yet.
- Future visits after Nov 6 are scheduled only. They are not in the completion rate or the pace actual.
- A few Northwind rows are messy on purpose: duplicate ingests, blank visit types, a backward clock, and upper case status. Harborline quarter rows stay clean so the median stays locked.
- Days elapsed counts Oct 1 and Nov 6. That is 37 days. The quarter has 92 days.

The page prints the warehouse result. If a quota and a mart ever disagreed, the page would show the mart.

## Tests

`make all` runs `dbt build`. This build passed 164 checks, including 138 data tests and 26 models.

The tests cover unique keys, nulls, relationships, and accepted values. Singular tests cover payer isolation, the other payers still existing upstream, the status cutoffs, each goal matching its fact table, a cumulative pace line that does not fall, complete weeks only on the sparklines, staging repairs, and action sentences that contain the mart number.

## Layout

```
assumptions/          generation settings and goal targets
config/               profile.json and company.json
payer_model/          generate.py and export_site.py
dbt/models/staging/   cleaned sources
dbt/models/intermediate/
dbt/models/marts/     one payer, goals, pace, actions
dbt/models/semantic.yml
dbt/analyses/         Snowflake row access example
dbt/tests/            singular tests
site/                 index.html, styles, data.js, architecture.png
```

Copy for the header, the disclaimer, and the about card lives in `config/`. Edit it there and run `make all` again.
