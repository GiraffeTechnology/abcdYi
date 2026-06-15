# Participant Roles — abcdYi

abcdYi uses a role-based participant model. Each participant can have one or more roles that determine how they are matched, scored, and tracked.

---

## Available Roles

### MANUFACTURER
Garment factories and production workshops that execute the main production run.

- **Matching dimensions used:** category_fit, fabric_capability_fit, quantity_fit, moq_fit, capacity_fit, lead_time_fit, location_fit, trade_term_fit, quality_history_fit, on_time_delivery_fit
- **Typical profile fields:** product_categories, fabric_types, moq_pcs, production_capacity_pcs_per_month, lead_time_days, trade_terms, quality_certifications
- **In the workflow:** Receives RFQs for garment_manufacturing section; contributes production_time_days to lead time calculation

### FABRIC_SUPPLIER
Fabric mills and textile wholesalers supplying woven, knit, or specialty fabrics.

- **Matching dimensions:** category_fit, fabric_capability_fit, moq_fit, lead_time_fit, location_fit, trade_term_fit
- **Typical profile fields:** fabric_types, moq_pcs, lead_time_days
- **In the workflow:** Contributes fabric_lead_time_days (parallel stage) to lead time calculation

### TRIM_SUPPLIER
Suppliers of buttons, zippers, labels, hangtags, elastic, and other accessories.

- **Matching dimensions:** moq_fit, lead_time_fit, location_fit
- **Typical profile fields:** product_categories (trim types), moq_pcs, lead_time_days
- **In the workflow:** Contributes trim_lead_time_days (parallel stage) to lead time calculation

### PACKAGING_SUPPLIER
Suppliers of poly bags, cartons, hangers, tissue paper, and other packaging materials.

- **Matching dimensions:** moq_fit, lead_time_fit, location_fit
- **Typical profile fields:** product_categories (packaging types), moq_pcs, lead_time_days
- **In the workflow:** Contributes packaging_lead_time_days (parallel stage) to lead time calculation

### LOGISTICS_PROVIDER
Freight forwarders, shipping lines, air cargo carriers, and customs brokers.

- **Matching dimensions:** trade_term_fit, location_fit, lead_time_fit
- **Typical profile fields:** trade_terms, routes, lead_time_days
- **In the workflow:** Contributes logistics_time_days (sequential stage) to lead time calculation

### QC_INSPECTOR
Third-party quality control and inspection firms.

- **Matching dimensions:** location_fit, lead_time_fit, quality_history_fit
- **Typical profile fields:** inspection_types, certifications, lead_time_days
- **In the workflow:** Contributes qc_time_days; assigned to QC records; quality incidents tracked

### BUYER
The brand, designer, or trading company placing the order.

- **In the workflow:** Creates buyer inquiries; confirms orders; signs off on delivery; triggers supplier memory updates

### AGENT
Sourcing agents or intermediaries coordinating between buyers and manufacturers.

- **In the workflow:** May create RFQs, coordinate supplier responses, and manage order execution on behalf of buyers

---

## Role Assignment

```http
POST /api/participants/{id}/roles
{"role_name": "MANUFACTURER"}
```

A participant can hold multiple roles. Role history is tracked per participant.

---

## How Roles Affect Matching

The matching engine scores each participant against each production section of the order. The section determines which dimensions are most relevant:

| Section | Primary Role | Key Lead Time Field |
|---|---|---|
| fabric_sourcing | FABRIC_SUPPLIER | fabric_lead_time_days |
| trims_sourcing | TRIM_SUPPLIER | trim_lead_time_days |
| packaging_sourcing | PACKAGING_SUPPLIER | packaging_lead_time_days |
| garment_manufacturing | MANUFACTURER | production_time_days |
| qc_inspection | QC_INSPECTOR | qc_time_days |
| logistics | LOGISTICS_PROVIDER | logistics_time_days |

---

## Supplier Memory

Performance is tracked per participant across orders:

- `qc_pass_rate` — ratio of QC_PASSED records
- `on_time_delivery` — whether orders were delivered on time
- `response_time_hours` — time from RFQ sent to response received
- `quality_issue_count` — cumulative quality incident count

At 3 quality incidents, a `ReplacementAlert` is created and an approval request is generated for the buyer to decide on supplier replacement.
