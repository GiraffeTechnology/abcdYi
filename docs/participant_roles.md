# Participant Roles — abcdYi

abcdYi uses a role-based participant model. Each participant in the system can hold one or more roles that determine how they are matched to orders, what actions they can take in the workflow, what data they can see, and how their performance is tracked over time.

---

## All Participant Roles

### MANUFACTURER

**Description:** Garment factories, CMT (cut, make, trim) operations, knitting mills, weaving mills, and production workshops that execute the primary manufacturing work for an order.

**Typical use case in apparel and textile:** A CMT factory in Guangzhou that receives cut fabric, trims, and a tech pack, then produces finished garments. Or a knitting mill that produces sweater bodies for a small fashion brand.

**How they participate in the workflow:**
- Receives the main RFQ for the production section of the order
- Submits a quotation with unit price, lead time, MOQ, and production capacity
- Sets production milestones (CUTTING, SEWING, WASHING, IRONING, FINAL_QC, PACKING) and reports progress against them
- Submits production updates and receives expedite alerts if delays are predicted

**Effect on matching score:** Matching dimensions include product category alignment, fabric capability fit, quantity fit relative to MOQ, capacity fit for the order volume, lead time fit, location (proximity to fabric/trim suppliers), trade term support, and historical QC pass rate and on-time delivery rate from supplier memory.

---

### FABRIC_SUPPLIER

**Description:** Fabric mills, textile wholesalers, and converters supplying woven, knitted, non-woven, or specialty fabrics.

**Typical use case in apparel and textile:** A denim mill supplying 14oz selvedge denim to an independent brand for a small-batch jeans run. Or a jersey knit wholesaler supplying fabric for a 300-unit T-shirt production.

**How they participate in the workflow:**
- Receives a fabric-specific RFQ with fabric specification, quantity, colorway, and delivery-to-factory date
- Submits a quotation with price per meter/yard, available lead time, MOQ, and any composition or construction deviations from the spec
- Reports the FABRIC_BOOKING milestone when fabric is confirmed, and fabric-in-house when ready

**Effect on matching score:** `fabric_lead_time_days` is a parallel input to the total lead time calculation. A fabric supplier with a 20-day lead time versus one with 12 days can shift the critical path of the entire production schedule. Matching also considers fabric type capability, MOQ fit, and location relative to the factory.

---

### TRIM_SUPPLIER

**Description:** Suppliers of garment trims and accessories: buttons, zippers, labels (woven, printed, heat-transfer), patches, elastic, drawcords, snap fasteners, velcro, rivets, and hangtags.

**Typical use case in apparel and textile:** A Yiwu-based accessories supplier providing custom woven labels and metal buttons for a capsule collection. Or a zipper specialist supplying YKK zippers for a 500-unit outerwear run.

**How they participate in the workflow:**
- Receives a trim-specific RFQ listing each trim component, specification, quantity, and required delivery date
- Submits a quotation per component or as a bundle, with lead time and MOQ per item
- Reports TRIM_BOOKING milestone and trim-in-house confirmation

**Effect on matching score:** `trim_lead_time_days` is a parallel input to total lead time. Custom trims (woven labels, embossed buttons) have longer lead times than stock items. Matching considers product category (trim types supplied), MOQ fit, and location relative to the factory.

---

### PACKAGING_SUPPLIER

**Description:** Suppliers of polybags, garment boxes, shipping cartons, tissue paper, hangers, sticker labels, and price tags.

**Typical use case in apparel and textile:** A packaging supplier providing branded polybags with hang holes and custom-printed shipping boxes for a DTC brand's seasonal drop. Or a hanger supplier providing branded plastic hangers for a retail-ready shipment.

**How they participate in the workflow:**
- Receives a packaging RFQ with specifications for each packaging component (dimensions, print specs, branding requirements), quantities, and required in-factory date
- Submits a quotation with lead time per item and MOQ
- Reports PACKAGING_BOOKING milestone and packaging-in-house confirmation

**Effect on matching score:** `packaging_lead_time_days` is a parallel input to total lead time. Custom printing adds lead time; stock packaging ships faster. Matching considers product categories (packaging types), MOQ fit, and proximity to the factory.

---

### LOGISTICS_PROVIDER

**Description:** Freight forwarders, air cargo carriers, ocean freight consolidators, express courier services, and last-mile delivery providers.

**Typical use case in apparel and textile:** A freight forwarder in Shenzhen arranging LCL (less-than-container-load) ocean freight for a 500-unit designer order shipping to a studio in London. Or an express courier service for a fast-track air shipment.

**How they participate in the workflow:**
- Engaged after QC clearance to arrange shipment booking
- Receives the packing list and shipping documentation for review at the SHIPMENT_HANDOVER milestone
- Provides tracking information back into the system after goods are shipped
- A `SHIPMENT_APPROVE` human approval gate governs the release of goods to the logistics provider

**Effect on matching score:** `logistics_time_days` is a sequential stage added to the total lead time after production and QC. Matching considers trade term support (FOB, CIF, DAP), route coverage, and lead time for the specific shipping lane.

---

### QC_INSPECTOR

**Description:** Third-party quality control and inspection firms, and independent QC inspectors, who conduct inline and final inspections of garments and goods before shipment.

**Typical use case in apparel and textile:** A third-party inspection agency conducting a final random inspection (AQL Level II) of a 500-unit order at the factory before shipment. Or a freelance QC inspector conducting an inline check at the sewing stage of a 1,000-unit order.

**How they participate in the workflow:**
- Assigned to the QC section of the order at participant classification
- Receives the QC standard for the order (measurement tolerances, AQL level, defect classification)
- Submits a QC record with measurement report, defect counts by category, and photographic evidence
- A QC_PASSED result advances the order to delivery handover; QC_FAILED triggers either a rework loop or a `QC_ESCALATE` approval request
- Quality incident history is tracked per inspector in supplier memory

**Effect on matching score:** Matching considers inspection type capability (inline, final, packing), relevant certifications (e.g., SGS, Bureau Veritas accreditation), geographic proximity to the factory, and quality incident history.

---

### BUYER

**Description:** The brand, designer, or trading company that originates the order and makes the commercial decisions throughout the workflow.

**Typical use case in apparel and textile:** An independent designer placing a 300-unit production order for a signature jacket. Or a small brand sourcing a 10-style capsule collection with a single CMT factory and multiple fabric suppliers.

**How they participate in the workflow:**
- Creates or submits the buyer inquiry that initiates the order
- Fills out or reviews the dynamic order form
- Receives and reviews decision packets before supplier selection
- Provides the final `BUYER_SIGNOFF` approval to close the order
- Buyer sign-off triggers the supplier memory update for all participating suppliers on the order

---

### AGENT

**Description:** Sourcing agents, trading companies, and intermediaries who coordinate between buyers and manufacturers on behalf of the buyer.

**Typical use case in apparel and textile:** A Hong Kong-based sourcing agent managing production across five factories in mainland China on behalf of a European brand. The agent reviews and approves RFQs, monitors production, and submits buyer sign-off.

**How they participate in the workflow:**
- May act with delegated authority on behalf of the buyer for RFQ approval, quote approval, order confirmation, and other gates
- Coordinates supplier responses and milestone reporting
- May submit buyer sign-off with explicit buyer delegation

---

## Role Assignment via API

A participant can hold multiple roles. Roles are assigned per participant, not per order — a factory that also handles logistics can hold both MANUFACTURER and LOGISTICS_PROVIDER roles.

```http
POST /api/participants/{id}/roles
{"role_name": "MANUFACTURER"}
```

Role history is tracked in the `participant_roles` table, with `is_active` flag per role.

---

## How Roles Affect Matching Scores

The matching engine scores each candidate participant against a specific production section of the order. The section determines which profile dimensions are evaluated and which lead time field the participant contributes to the total lead time calculation.

| Production Section | Role | Lead Time Contribution | Calculation Type |
|---|---|---|---|
| fabric_sourcing | FABRIC_SUPPLIER | `fabric_lead_time_days` | Parallel (max) |
| trims_sourcing | TRIM_SUPPLIER | `trim_lead_time_days` | Parallel (max) |
| packaging_sourcing | PACKAGING_SUPPLIER | `packaging_lead_time_days` | Parallel (max) |
| garment_manufacturing | MANUFACTURER | `production_time_days` | Sequential (sum) |
| qc_inspection | QC_INSPECTOR | `qc_time_days` | Sequential (sum) |
| logistics | LOGISTICS_PROVIDER | `logistics_time_days` | Sequential (sum) |

Matching scores are stored in the `participant_matches` table with a full `score_breakdown` JSONB column recording how each dimension contributed to the final score. The breakdown enables human reviewers to understand why a particular supplier was ranked first or flagged with a risk warning.
