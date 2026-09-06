"""Validated output contract for the OSB analysis agent."""

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    source_file: str = Field(description="Exact attachment filename or JIRA_DESCRIPTION")
    finding: str


class Operation(StrictModel):
    name: str
    protocol: str
    request_contract: str
    response_contract: str
    soap_action: str
    evidence: list[Evidence]


class BackendCall(StrictModel):
    name: str
    protocol: str
    endpoint: str
    timeout: str
    evidence: list[Evidence]


class Transformation(StrictModel):
    source_file: str
    purpose: str
    mappings: list[str]
    evidence: list[Evidence]


class ErrorBehavior(StrictModel):
    condition: str
    source_behavior: str
    mule_behavior: str
    evidence: list[Evidence]


class RequirementAnalysis(StrictModel):
    objective: str
    requirements: list[str]
    acceptance_criteria: list[str]
    missing_information: list[str]


class SourceAnalysis(StrictModel):
    service_name: str
    protocols: list[str]
    operations: list[Operation]
    data_model_findings: list[str]
    backends: list[BackendCall]
    transformations: list[Transformation]
    error_behaviors: list[ErrorBehavior]
    dependencies: list[str]


class MuleDesign(StrictModel):
    interface_strategy: str
    inbound_endpoint: str
    flows: list[str]
    mule_components: list[str]
    dataweave_modules: list[str]
    configuration_properties: list[str]
    error_handling: list[str]
    munit_tests: list[str]
    kafka_required: bool
    kafka_reason: str
    unanswered_decisions: list[str]


class MigrationAnalysis(StrictModel):
    executive_summary: str
    requirement_analysis: RequirementAnalysis
    source_analysis: SourceAnalysis
    mule_design: MuleDesign
    risks: list[str]
    assumptions: list[str]
