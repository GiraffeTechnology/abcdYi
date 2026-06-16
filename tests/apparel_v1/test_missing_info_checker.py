"""Unit tests for the missing information checker."""
import pytest
from src.apparel_v1.inquiry_intake import intake_inquiry, CANONICAL_INQUIRY
from src.apparel_v1.requirement_extractor import extract_requirements, ExtractedRequirements
from src.apparel_v1.missing_info_checker import check_missing_info, MissingInfoReport, REQUIRED_FIELDS


class TestCheckMissingInfo:
    def setup_method(self):
        inq = intake_inquiry(CANONICAL_INQUIRY)
        self.req = extract_requirements(inq)
        self.report = check_missing_info(self.req)

    def test_returns_missing_info_report(self):
        assert isinstance(self.report, MissingInfoReport)

    def test_inquiry_id_linked(self):
        assert self.report.inquiry_id == self.req.inquiry_id

    def test_canonical_mostly_complete(self):
        # Canonical inquiry covers most required fields
        assert self.report.completeness_score >= 0.75

    def test_completeness_score_range(self):
        assert 0.0 <= self.report.completeness_score <= 1.0

    def test_questions_match_missing_fields(self):
        assert len(self.report.clarification_questions) == len(self.report.missing_fields)

    def test_fully_populated_requirements(self):
        req = ExtractedRequirements(
            inquiry_id="TEST-001",
            product_type="Shirt",
            quantity=10000,
            fabric_type="100% cotton",
            color="white",
            size_range="S/M/L/XL",
            delivery_deadline_days=45,
            trade_term="FOB",
            destination="China",
        )
        report = check_missing_info(req)
        assert report.is_complete is True
        assert report.missing_fields == []
        assert report.completeness_score == 1.0

    def test_empty_requirements_has_all_missing(self):
        req = ExtractedRequirements(inquiry_id="EMPTY-001")
        report = check_missing_info(req)
        assert report.is_complete is False
        assert len(report.missing_fields) == len(REQUIRED_FIELDS)
        assert report.completeness_score == 0.0

    def test_questions_are_non_empty_strings(self):
        if self.report.clarification_questions:
            for q in self.report.clarification_questions:
                assert isinstance(q, str)
                assert len(q) > 5
