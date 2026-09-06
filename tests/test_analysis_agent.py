import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.analysis_agent import adf_to_text, analyze, build_input, write_outputs
from orchestrator.models import MigrationAnalysis


def sample_analysis() -> MigrationAnalysis:
    return MigrationAnalysis.model_validate({
        "executive_summary": "CustomerLookup is a synchronous SOAP service.",
        "requirement_analysis": {
            "objective": "Design the service on MuleSoft.",
            "requirements": ["Preserve the SOAP contract."],
            "acceptance_criteria": ["The operation remains available."],
            "missing_information": ["Backend timeout is not documented."],
        },
        "source_analysis": {
            "service_name": "CustomerLookup",
            "protocols": ["SOAP"],
            "operations": [{
                "name": "getCustomer", "protocol": "SOAP",
                "request_contract": "GetCustomerRequest",
                "response_contract": "GetCustomerResponse",
                "soap_action": "getCustomer",
                "evidence": [{"source_file": "Customer.wsdl", "finding": "Defines getCustomer."}],
            }],
            "data_model_findings": ["customerId is required."],
            "backends": [], "transformations": [], "error_behaviors": [],
            "dependencies": [],
        },
        "mule_design": {
            "interface_strategy": "Preserve the SOAP interface.",
            "inbound_endpoint": "UNKNOWN",
            "flows": ["SOAP request", "Validation", "Backend call", "Response mapping"],
            "mule_components": ["Web Service Consumer"],
            "dataweave_modules": ["Customer response mapping"],
            "configuration_properties": ["backend.timeout"],
            "error_handling": ["Map backend timeout to the existing SOAP fault."],
            "munit_tests": ["Valid customer", "Backend timeout"],
            "kafka_required": False,
            "kafka_reason": "No asynchronous requirement exists.",
            "unanswered_decisions": ["Confirm backend timeout."],
        },
        "risks": ["XQuery mapping parity."],
        "assumptions": [],
    })


class AnalysisAgentTests(unittest.TestCase):
    def test_adf_to_text(self):
        adf = {"type": "doc", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "Preserve the contract."}
        ]}]}
        self.assertEqual(adf_to_text(adf), "Preserve the contract.")

    def test_build_input_labels_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "1-Customer.wsdl").write_text("<definitions/>", encoding="utf-8")
            prompt = build_input(
                {"issue": "KAN-1", "title": "Migrate", "description": None},
                "CustomerLookup", root,
                [{"originalName": "Customer.wsdl", "storedName": "1-Customer.wsdl"}],
            )
        self.assertIn("SERVICE REQUESTED BY USER: CustomerLookup", prompt)
        self.assertIn("SOURCE FILE: Customer.wsdl", prompt)

    def test_write_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            outputs = write_outputs(sample_analysis(), {"model": "test"}, Path(folder))
            self.assertTrue(all(path.exists() for path in outputs.values()))
            payload = json.loads(outputs["combined"].read_text(encoding="utf-8"))
            self.assertEqual(payload["analysis"]["source_analysis"]["service_name"], "CustomerLookup")

    def test_analyze_uses_structured_response_without_storage(self):
        class FakeResponses:
            def __init__(self):
                self.arguments = None

            def parse(self, **kwargs):
                self.arguments = kwargs
                return type("Response", (), {
                    "output_parsed": sample_analysis(),
                    "id": "resp_test",
                    "usage": None,
                })()

        responses = FakeResponses()
        client = type("Client", (), {"responses": responses})()
        with tempfile.TemporaryDirectory() as folder:
            result, metadata = analyze(
                {"issue": "KAN-1", "title": "Migrate", "description": None},
                "CustomerLookup", Path(folder), [],
                {"OPENAI_MODEL": "gpt-test"}, client=client,
            )
        self.assertEqual(result.source_analysis.service_name, "CustomerLookup")
        self.assertEqual(metadata["responseId"], "resp_test")
        self.assertFalse(responses.arguments["store"])
        self.assertIs(responses.arguments["text_format"], MigrationAnalysis)


if __name__ == "__main__":
    unittest.main()
