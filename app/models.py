from typing import List, Optional

from pydantic import BaseModel, Field


class Issue(BaseModel):
    title: str
    category: str = "CRO"
    severity: str = "Medium"
    primary_kpi: str = "CVR"
    secondary_kpi: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    why_it_matters: str = ""
    recommendation: str = ""
    expected_impact: str = ""


class PageAudit(BaseModel):
    page_name: str
    url: str
    issues: List[str] = Field(default_factory=list)
    priority: str = "P2"
    summary: str = ""
    screenshot_path: Optional[str] = None
    proposed_screenshot_path: Optional[str] = None


class AOVOpportunity(BaseModel):
    title: str
    placement: str
    description: str
    expected_impact: str = "medium"


class Recommendation(BaseModel):
    title: str
    detail: str
    priority: str = "P2"


class AuditReport(BaseModel):
    brand_name: str
    website_url: str
    executive_summary: str
    pages: List[PageAudit]
    aov_opportunities: List[AOVOpportunity]
    recommendations: List[Recommendation]
    deck_outline: List[str]
    findings: List[Issue] = Field(default_factory=list, max_length=8)
