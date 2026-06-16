"""Unit tests for upstream planning module."""
import pytest
from src.apparel_v1.inquiry_intake import intake_inquiry, CANONICAL_INQUIRY
from src.apparel_v1.requirement_extractor import extract_requirements
from src.apparel_v1.upstream_planner import (
    plan_upstream,
    resolve_m_side_roles,
    plan_upstream_dependencies,
    generate_supplier_inquiries,
    UpstreamPlan,
    MRoleContext,
    UpstreamDependency,
)


class TestResolveRoles:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        self.roles = resolve_m_side_roles(self.req)

    def test_returns_list_of_roles(self):
        assert isinstance(self.roles, list)
        assert all(isinstance(r, MRoleContext) for r in self.roles)

    def test_includes_merchandiser(self):
        role_names = [r.role for r in self.roles]
        assert "merchandiser" in role_names

    def test_includes_garment_factory(self):
        role_names = [r.role for r in self.roles]
        assert "garment_factory" in role_names

    def test_includes_fabric_sourcer_for_cotton(self):
        role_names = [r.role for r in self.roles]
        assert "fabric_sourcer" in role_names

    def test_includes_logistics_for_fob(self):
        role_names = [r.role for r in self.roles]
        assert "logistics_coordinator" in role_names

    def test_all_roles_have_responsibilities(self):
        for role in self.roles:
            assert len(role.responsibilities) > 0

    def test_all_roles_have_actor_id(self):
        for role in self.roles:
            assert role.actor_id


class TestPlanDependencies:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        self.deps = plan_upstream_dependencies(self.req)

    def test_returns_list_of_dependencies(self):
        assert isinstance(self.deps, list)
        assert all(isinstance(d, UpstreamDependency) for d in self.deps)

    def test_has_fabric_dependency(self):
        types = [d.dependency_type for d in self.deps]
        assert "fabric" in types

    def test_has_production_dependency(self):
        types = [d.dependency_type for d in self.deps]
        assert "production" in types

    def test_has_qc_dependency(self):
        types = [d.dependency_type for d in self.deps]
        assert "qc_inspection" in types

    def test_has_logistics_dependency(self):
        types = [d.dependency_type for d in self.deps]
        assert "logistics" in types

    def test_all_dependencies_have_unique_ids(self):
        ids = [d.dependency_id for d in self.deps]
        assert len(ids) == len(set(ids))

    def test_sequential_dependencies_in_chronological_order(self):
        # Sequential deps (production → qc → logistics) must have strictly increasing deadlines.
        # Parallel deps (fabric, trim) may have any order relative to each other.
        sequential_types = ("production", "qc_inspection", "logistics")
        sequential = [d for d in self.deps if d.dependency_type in sequential_types]
        days = [d.required_by_day for d in sequential]
        for i in range(1, len(days)):
            assert days[i] >= days[i - 1], (
                f"Sequential dep at index {i} ({days[i]}d) "
                f"must not precede prior dep ({days[i-1]}d)"
            )


class TestGenerateSupplierInquiries:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        roles = resolve_m_side_roles(self.req)
        self.inquiries = generate_supplier_inquiries(self.req, roles)

    def test_returns_list_of_dicts(self):
        assert isinstance(self.inquiries, list)
        assert all(isinstance(i, dict) for i in self.inquiries)

    def test_at_least_two_inquiries(self):
        assert len(self.inquiries) >= 2

    def test_fabric_inquiry_present(self):
        roles = [i["target_role"] for i in self.inquiries]
        assert "fabric_supplier" in roles

    def test_factory_inquiry_present(self):
        roles = [i["target_role"] for i in self.inquiries]
        assert "garment_factory" in roles

    def test_each_inquiry_has_required_fields_list(self):
        for inq in self.inquiries:
            assert "required_fields_from_supplier" in inq
            assert len(inq["required_fields_from_supplier"]) > 0

    def test_inquiry_body_contains_quantity(self):
        for inq in self.inquiries:
            assert "10,000" in inq["body"] or "10000" in inq["body"]


class TestPlanUpstream:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        self.plan = plan_upstream(self.req)

    def test_returns_upstream_plan(self):
        assert isinstance(self.plan, UpstreamPlan)

    def test_plan_id_assigned(self):
        assert self.plan.plan_id.startswith("PLAN-")

    def test_has_m_roles(self):
        assert len(self.plan.m_roles) > 0

    def test_has_dependencies(self):
        assert len(self.plan.dependencies) > 0

    def test_has_supplier_inquiries(self):
        assert len(self.plan.supplier_inquiries) > 0

    def test_total_days_positive(self):
        assert self.plan.total_upstream_days_estimate > 0
