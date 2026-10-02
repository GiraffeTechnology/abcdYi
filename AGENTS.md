# AGENTS.md — abcdYi Repository Instructions

## Source of truth

Read `docs/Giraffe_Agent_MVP_v1.0_PRD.md` before changing product behavior. Despite the historical filename, its current header and version identify the complete active abcdYi PRD. GitHub Issue #25 records the v2.0 product positioning; the PRD states the detailed current application boundary and acceptance criteria. Do not use superseded Git history or older documents to expand current scope.

All new or revised GitHub text in this repository—code comments, documentation, commits, issues, PR titles and descriptions, and review comments—must be in English. Preserve historical records as history; do not translate or rewrite unrelated files merely to enforce this rule.

A product-scope change must update the PRD as a coherent whole. Do not append a small exception, patch note, or conflicting addendum that leaves earlier requirements in force. Keep the definitions, functional requirements, service ownership, exclusions, and acceptance criteria consistent in the same revision.

## Product boundary

abcdYi is Giraffe Agent's first vertical application, limited to apparel and textile order execution. Its users include professional buyers, brands, designers, apparel and textile manufacturers, and their production partners. Do not describe mechanical machining, CAD/CNC, generic industry orders, or other vertical applications as abcdYi deliverables.

Aivan is the pre-contract front-end part of abcdYi. It owns RFQ intake, requirement clarification, supplier inquiry and reply handling, lead-time invocation, option presentation, and human approval before a formal contract is generated. Aivan's independent repository and service process do not turn it into a separate end-to-end product within this application.

The formal contract is a hard handoff boundary. An approved proposal is not a signed contract or a confirmed production order. abcdYi owns the versioned contract handoff and post-contract apparel and textile execution: production milestones, QC, logistics, buyer sign-off, and supplier-performance evidence.

OpenClaw is the gateway and runtime. Messaging services are channels. Do not list OpenClaw as a peer channel.

## Service and evidence rules

- GLTG is an API-connected lead-time dependency. Preserve its canonical P50/P80/P90, scenarios, risk explanation, and source references. Do not duplicate its numerical engine inside Aivan or abcdYi.
- giraffe-db is the API-connected authoritative business-fact and evidence service. Preserve tenant and service identity, write/readback semantics, lineage, and truthful persistence status. A local draft or successful HTTP response alone does not establish authoritative durable storage.
- Aivan's browser must not connect directly to GLTG or giraffe-db. Do not replace service APIs with cross-repository imports or direct reads of another service's tables.
- Bind an approval to the exact draft or contract version, actor, role, and time. Human approval is required for outbound commercial commitments and material changes to price, delivery, or quality.
- Keep original evidence, revisions, corrections, failures, and synthetic-data labels distinguishable. A delivered tracking event does not constitute buyer acceptance.

## Delivery and verification

Map changes to the active PRD and name the affected acceptance criterion. Verify the smallest meaningful workflow and report exact revisions, commands, results, failures, and skipped integration steps. Do not present an unmerged PR, a mock-only run, or a previous candidate's result as current end-to-end acceptance.

Aivan's seven-step Stage 1 is a pre-contract delivery slice. Its completion does not establish full abcdYi contract and post-contract acceptance. Keep those evidence claims separate. For joint integration, use the actual Aivan, GLTG, and giraffe-db APIs and identify their exact revisions. Do not change production hosts, credentials, or external channels as part of a documentation-only task.
