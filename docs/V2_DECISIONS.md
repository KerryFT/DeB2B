# V2 decisions

## Shared PostgreSQL derived-data foundation

Use tenant-owned PostgreSQL tables for feature snapshots, model/prediction runs and jobs. This
keeps one point-in-time and provenance contract across all seven capabilities without introducing
a warehouse or feature-store service. Raw email/document content is not copied into features.

## Statistical baseline before complex ML

Probability-to-pay uses a smoothed segment baseline with explicit 7/14/30-day labels and
calibration metrics. Cash-flow is derived deterministically from invoice components and those
probabilities. An advanced challenger may replace it only after time-split evaluation beats the
recorded champion by the configured minimum improvement.

## Automation has independent safety locks

Tenant policy defaults to `disabled` with its kill switch on. Global kill and external delivery are
separate environment controls and both default safe. Shadow decisions never enqueue; enabling
canary/enabled requires admin permission and an explicit confirmation phrase. Sending remains a
separate port and is not exposed by the V2 demo API.

## Neutral descriptive analytics

Customer segments are limited to `consistent`, `variable`, and `insufficient_data`. Account-manager
metrics are coaching data with raw/adjusted values and minimum cohort suppression, never an HR
rating. Dispute causes are labeled as evidence-backed inference rather than proven causation.
