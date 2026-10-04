# AGENTS.md — abcdYi Repository Instructions

## Source of truth

Read `docs/Giraffe_Agent_MVP_v1.0_PRD.md` before changing product behavior. The product owner's current instructions and original AIVAN and abcdYi product descriptions take precedence over this working PRD. GitHub Issue #25 and historical Git revisions are context, not independent authority for a product definition or gate. Reconcile conflicts with the original definitions and current instructions.

All currently tracked repository text and all new or revised GitHub text must be in English, including documentation, code comments, reports, commits, issues, PR descriptions, and review comments. Existing Git history is not rewritten. Translate tracked content without deleting code or data. Preserve runtime behavior and the meaning of evidence and multilingual tests; identify compatibility-sensitive identifiers, protocol values, and fixtures for an explicit migration plan rather than silently changing their semantics.

Inventory code outside the approved product scope, identify exact source revisions and paths, and freeze it for preservation. Do not delete it or treat its presence as an active delivery requirement. Preserve shared in-scope behavior when identifying mixed-purpose modules.

A product-scope change must update the PRD as a coherent whole. Do not append a small exception, patch note, or conflicting addendum that leaves earlier requirements in force. Keep the definitions, functional requirements, service ownership, exclusions, and acceptance criteria consistent in the same revision.

## Product boundary

abcdYi is Giraffe Agent's first vertical application, limited to apparel and textile order execution. Its users include professional buyers, brands, designers, apparel and textile manufacturers, and their production partners. Do not describe mechanical machining, CAD/CNC, generic industry orders, or other vertical applications as abcdYi deliverables.

Aivan is the Giraffe Agent front-end application for inquiry, quotation, and order confirmation. abcdYi's front end calls Aivan. myAivan is Aivan's web version. OpenClaw-aivan is Aivan's IM and email access dependency. Keep these product relationships distinct from repository layout or deployment choices.

The execution flow is approved quotation → order confirmation → production. An approved proposal is not yet a confirmed order. Do not add a formal contract, contract identifier, signature, or contract-confirmation state as a production prerequisite. abcdYi owns apparel and textile execution: production milestones, QC, logistics, buyer sign-off, and supplier-performance evidence.

OpenClaw is the gateway and runtime. Messaging services are channels. Do not list OpenClaw as a peer channel.

The product's standard working and interaction language is English. Translate non-English input through `giraffe-language-skill` into standard English before workflow processing; translate non-English output dynamically through the same module. Do not replace this with static language packs or make complete all-language translation coverage a delivery prerequisite. Except for company and user profile information, do not store non-English content in the database, including business history, process data, drafts, messages, and events. Preserve source references, content hashes, and English-normalized evidence; do not create raw-original fields or side tables that bypass this rule.

## Service and evidence rules

- GLTG and GPM are Aivan dependency modules called through APIs. Preserve their returned analysis and source references. Do not turn them into independent product requirements or make whole-platform production acceptance a prerequisite for an Aivan front-end delivery.
- Giraffe Agent, Aivan, and abcdYi depend on the same extensible, dynamic private-data design: the database records business history and business-process data and is their business source of truth. Persist and recover workflow state through that database, not conversation context. giraffe-db is hot-swappable for the user's own private database through the provider interface. Preserve tenant and service identity, authorization, read/write semantics, lineage, and truthful persistence status across providers. A local draft or successful HTTP response alone does not prove durable storage.
- Keep dependency and private-data access within authorized API and provider interfaces. Do not impose giraffe-db as the exclusive private-data provider.
- The two designated giraffe-db simulated databases, generated from real-data sources, are valid product-test and acceptance sources. Do not reject acceptance because these data are simulated or require live customer production data. Execute the actual application/API workflow and state transitions, including process-data write/readback and recovery after restart or reload without prior conversation context. These simulated databases behind actual executed APIs provide valid integration evidence; skipped jobs and fabricated outputs do not establish acceptance.
- Bind an approval to the exact draft or contract version, actor, role, and time. Human approval is required for outbound commercial commitments and material changes to price, delivery, or quality.
- Keep source references, content hashes, English-normalized evidence, revisions, corrections, failures, and synthetic-data labels distinguishable. Do not interpret evidence preservation as permission to store non-English business originals. A delivered tracking event does not constitute buyer acceptance.

## Delivery and verification

Map changes to the active PRD and name the affected acceptance criterion. Verify the smallest meaningful workflow and report exact revisions, commands, results, failures, and skipped integration steps. Do not present an unmerged PR, a mock-only run, or a previous candidate's result as current end-to-end acceptance.

Aivan's seven-step Stage 1 is an inquiry-and-quotation delivery slice. Its completion does not establish Aivan order-confirmation acceptance or the full abcdYi order lifecycle. Keep those evidence claims separate. For integration claims, identify the exact application revision, dependency APIs, and configured private-data provider actually exercised. Distinguish live evidence, mocks, failures, and skipped steps. Do not change production hosts, credentials, or external channels as part of a documentation-only task.

## CTYun TCP port 443 reservation

On CTYun hosts, TCP port 443 is owned by SSH. Do not stop, rebind, replace, or otherwise disrupt SSH.

- HTTP and HTTPS may use any port that is not in use, except 443. Do not block work waiting for a pre-approved web port: check which ports are free on the target, pick one, and pass it through configuration.
- Never bind HTTP, HTTPS, web servers, reverse proxies, or TLS listeners to 443.
- Do not hard-code a default port in code, configuration templates, gates, or documentation. Leave port values empty or as a `<PORT>` placeholder for the operator to fill in.
- A URL or origin without a port implies 443 for `https://`, so every public URL, origin, and CORS entry must state its port explicitly.
- Do not write examples that use port 443.

This constraint applies only to CTYun hosts; do not extend it to SIN or other environments without an explicit instruction. Recording this rule does not authorize changes to SSH, firewalls, credentials, network settings, or security settings.

In this repository the MyAivan web entry is the operator-supplied `VITE_MYAIVAN_URL`, which must state its port explicitly.
