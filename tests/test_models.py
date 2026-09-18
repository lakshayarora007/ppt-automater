from app.models import AuditReport, Issue, PageAudit


def test_page_audit_has_required_fields():
    page = PageAudit(
        page_name="Home",
        url="https://example.com",
        issues=["CTA not visible"],
        priority="P1",
        summary="Main landing page is too crowded.",
    )
    assert page.page_name == "Home"
    assert page.priority == "P1"
    assert page.issues[0] == "CTA not visible"


def test_audit_report_has_core_sections():
    audit = AuditReport(
        brand_name="Example Brand",
        website_url="https://example.com",
        executive_summary="Strong but uneven on mobile conversion.",
        pages=[],
        aov_opportunities=[],
        recommendations=[],
        deck_outline=[],
    )
    assert audit.brand_name == "Example Brand"
    assert audit.executive_summary.startswith("Strong")
    assert isinstance(audit.pages, list)


def test_issue_supports_pitch_ready_kpi_fields_and_audit_caps_findings():
    audit = AuditReport(
        brand_name="Example Brand",
        website_url="https://example.com",
        executive_summary="Summary",
        pages=[],
        aov_opportunities=[],
        recommendations=[],
        deck_outline=[],
        findings=[Issue(title=f"Finding {index}") for index in range(8)],
    )
    assert audit.findings[-1].primary_kpi == "CVR"
    assert len(audit.findings) == 8
