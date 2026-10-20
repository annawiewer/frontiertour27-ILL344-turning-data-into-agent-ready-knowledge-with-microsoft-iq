"""Offline regression checks for the notebook's read-only visual helpers."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from azure.search.documents.indexes.models import (
    KnowledgeBase,
    KnowledgeBaseModel,
    KnowledgeSourceReference,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
)
from azure.search.documents.knowledgebases.models import KnowledgeRetrievalMinimalReasoningEffort


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "notebooks"))
import lab_visuals as visuals


POLICY = "file-docs-knowledge-source"
INDEX = "supplier-evidence-knowledge-source"
WORK = "workiq-knowledge-source"


class VisualTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.get_knowledge_source.side_effect = lambda name: SimpleNamespace(
            kind=visuals.SOURCE_ROLES[name][0],
            search_index_parameters=SimpleNamespace(
                search_index_name=visuals.SOURCE_ROLES[name][2]
            ),
        )
        self.client.get_knowledge_base.return_value = SimpleNamespace(
            knowledge_sources=[SimpleNamespace(name=POLICY)],
            output_mode="answerSynthesis",
            models=[object()],
            retrieval_reasoning_effort=None,
        )
        self.display = patch.object(visuals, "display").start()
        self.addCleanup(patch.stopall)

    def html(self):
        return "\n".join(call.args[0].data for call in self.display.call_args_list)

    def test_architecture_uses_official_icon_diagram(self):
        with patch.object(visuals, "SVG") as svg:
            visuals.show_architecture("agent")
        svg.assert_called_once_with(filename=str(
            ROOT / "img" / "architecture" / "azure-agent.svg"
        ))
        caption = self.display.call_args_list[-1].args[0].data
        self.assertIn("Architecture in brief:", caption)
        self.assertIn("The KB has no model.", caption)
        self.assertIn("<strong>Step by step:</strong>", caption)
        self.assertIn("<ol>", caption)
        self.assertIn("knowledge_base_retrieve", caption)
        with self.assertRaisesRegex(ValueError, "Unknown architecture stage"):
            visuals.show_architecture("missing")

    def test_kb_read_back_and_sdk_wire_values(self):
        self.client.get_knowledge_source.side_effect = None
        self.client.get_knowledge_source.return_value = SearchIndexKnowledgeSource(
            name=INDEX,
            search_index_parameters=SearchIndexKnowledgeSourceParameters(
                search_index_name="supplier-evidence"
            ),
        )
        self.client.get_knowledge_base.return_value = KnowledgeBase(
            name="lab",
            knowledge_sources=[KnowledgeSourceReference(name=INDEX)],
            output_mode="answerSynthesis",
            models=[KnowledgeBaseModel()],
        )
        visuals.verify_knowledge_base(self.client, "lab", [INDEX])
        self.assertIn("Configuration verified", self.html())
        self.assertIn("Operational evidence", self.html())

    def test_configuration_mismatches_fail_without_success_display(self):
        kb = self.client.get_knowledge_base.return_value
        for field, bad, message in (
            ("knowledge_sources", [], "source membership differs"),
            ("output_mode", "extractiveData", "expected output mode"),
            ("models", [], "needs an attached model"),
        ):
            with self.subTest(field=field):
                original = getattr(kb, field)
                setattr(kb, field, bad)
                with self.assertRaisesRegex(RuntimeError, message):
                    visuals.verify_knowledge_base(self.client, "lab", [POLICY])
                setattr(kb, field, original)
        self.display.assert_not_called()

    def test_extractive_boundary_and_missing_reasoning(self):
        kb = self.client.get_knowledge_base.return_value
        kb.output_mode = "extractiveData"
        with self.assertRaisesRegex(RuntimeError, "must not have an attached model"):
            visuals.verify_knowledge_base(self.client, "lab", [POLICY], extractive=True)
        kb.models = []
        with self.assertRaisesRegex(RuntimeError, "minimal reasoning"):
            visuals.verify_knowledge_base(self.client, "lab", [POLICY], extractive=True)
        kb.retrieval_reasoning_effort = KnowledgeRetrievalMinimalReasoningEffort()
        visuals.verify_knowledge_base(self.client, "lab", [POLICY], extractive=True)
        self.assertIn("Attached models: 0", self.html())

    def test_source_kind_and_index_mismatch(self):
        self.client.get_knowledge_source.side_effect = None
        source = SimpleNamespace(
            kind="file",
            search_index_parameters=SimpleNamespace(search_index_name="wrong-index"),
        )
        self.client.get_knowledge_source.return_value = source
        with self.assertRaisesRegex(RuntimeError, "expected kind"):
            visuals.verify_sources(self.client, [INDEX])
        source.kind = "searchIndex"
        with self.assertRaisesRegex(RuntimeError, "expected index"):
            visuals.verify_sources(self.client, [INDEX])
        self.display.assert_not_called()

    def test_extractive_reasoning_from_service_dictionary(self):
        kb = self.client.get_knowledge_base.return_value
        kb.output_mode = "extractiveData"
        kb.models = []
        for effort in ({}, {"kind": "low"}, {"kind": None}):
            with self.subTest(effort=effort):
                kb.retrieval_reasoning_effort = effort
                with self.assertRaisesRegex(RuntimeError, "minimal reasoning"):
                    visuals.verify_knowledge_base(self.client, "lab", [POLICY], extractive=True)
        self.display.assert_not_called()
        kb.retrieval_reasoning_effort = {"kind": "minimal"}
        visuals.verify_knowledge_base(self.client, "lab", [POLICY], extractive=True)
        self.assertIn("Configuration verified", self.html())

    def test_service_errors_propagate(self):
        self.client.get_knowledge_base.side_effect = RuntimeError("access denied")
        with self.assertRaisesRegex(RuntimeError, "access denied"):
            visuals.verify_knowledge_base(self.client, "lab", [POLICY])
        self.display.assert_not_called()

    def test_ingestion_acceptance_is_not_searchability(self):
        self.client.get_knowledge_source_status.return_value = SimpleNamespace(
            synchronization_status="active"
        )
        self.client.list_knowledge_source_files.return_value = [
            SimpleNamespace(file_name="CAL-POL-PUR-001.pdf", file_size_bytes=123, error_message=None)
        ]
        visuals.show_file_ingestion(self.client, POLICY)
        self.assertIn("do not guarantee", self.html())
        self.assertIn("CAL-POL-PUR-001.pdf", self.html())

    def test_missing_and_failed_uploads_raise(self):
        self.client.get_knowledge_source_status.return_value = SimpleNamespace(
            synchronization_status="active"
        )
        for files, message in (
            ([], "No uploaded files"),
            ([SimpleNamespace(file_name="bad.pdf", file_size_bytes=3, error_message="<broken>")],
             "File processing failed"),
        ):
            with self.subTest(message=message):
                self.client.list_knowledge_source_files.return_value = files
                with self.assertRaisesRegex(RuntimeError, message):
                    visuals.show_file_ingestion(self.client, POLICY)
        self.assertIn("&lt;broken&gt;", self.html())

    def test_empty_activity_and_references_are_unverified(self):
        visuals.show_activity([])
        visuals.show_references([], [], [POLICY])
        self.assertIn("Source execution is unverified", self.html())
        self.assertIn("Grounding is unverified", self.html())
        self.assertIn("Not observed, not necessarily broken", self.html())

    def test_partial_activity_and_source_attribution(self):
        activities = [
            {"id": 1, "type": "file", "knowledgeSourceName": POLICY, "elapsedMs": 24},
            {"id": 2, "type": "workIQ", "knowledgeSourceName": WORK, "error": {"message": "denied"}},
            {"id": 3, "knowledgeSourceName": INDEX, "warning": "partial"},
        ]
        refs = [
            {"id": "0", "activitySource": "1", "sourceData": {"title": "Policy", "snippet": "Approve"}},
            {"id": "1", "activitySource": 99, "docName": "Unknown"},
        ]
        visuals.show_activity(activities)
        visuals.show_references(refs, activities, [POLICY, WORK, INDEX])
        html = self.html()
        for expected in (
            "24 ms", "Failed", "Warning", "Evidence returned", "Source error reported",
            "Warning reported", "Source attribution unresolved", "Raw references JSON",
        ):
            self.assertIn(expected, html)

    def test_called_without_references_is_not_evidence(self):
        visuals.show_references([], [{"id": 0, "knowledgeSourceName": POLICY}], [POLICY])
        self.assertIn("Called, no linked references", self.html())

    def test_html_escaping_and_unsafe_workplace_links(self):
        for target in (
            "javascript:alert(1)", "https://user:password@example.com", "//example.com", "https://[bad"
        ):
            with self.subTest(target=target):
                refs = [{
                    "id": "<script>alert(1)</script>", "activitySource": 1,
                    "sourceData": {
                        "title": "<img src=x onerror=alert(1)>",
                        "parts": [{"text": "<script>bad</script>",
                                   "data": {"citation": {"targetLink": target}}}],
                    },
                }]
                visuals.show_references(refs, [{"id": 1, "knowledgeSourceName": WORK}], [WORK])
                self.assertNotIn("<script>", self.html())
                self.assertNotIn("<img src=x", self.html())
                self.assertIn("no safe HTTPS link", self.html())
        self.assertNotIn("href='javascript:", self.html())

    def test_workplace_link_and_pdf_pages(self):
        refs = [{
            "id": 0, "sourceData": {
                "title": "Policy", "page_number_from": 2, "page_number_to": 4,
                "parts": [{"data": {"citation": {"targetLink": "https://example.com/item?a=1&b=2"}}}],
            },
        }]
        visuals.show_references(refs, [], [POLICY])
        self.assertIn("pages 2 to 4", self.html())
        self.assertIn("https://example.com/item?a=1&amp;b=2", self.html())
        self.assertIn("noopener noreferrer", self.html())

    def test_file_reference_without_source_data_keeps_citation_target(self):
        visuals.show_references(
            [{"id": "file-0", "docName": "CAL-POL-PUR-001.pdf",
              "citationUrl": "https://example.com/policy", "activitySource": 0}],
            [{"id": 0, "knowledgeSourceName": POLICY}], [POLICY],
        )
        self.assertIn("CAL-POL-PUR-001.pdf", self.html())
        self.assertIn("href='https://example.com/policy'", self.html())
        self.assertIn("Evidence returned", self.html())

    def test_portal_links_are_local_and_encoded(self):
        visuals.show_portal_links(
            "https://lab.search.windows.net",
            search_resource_id="/subscriptions/sample/resourceGroups/lab",
            workspace_id="workspace",
            ontology_id="ontology",
            app_id="app'><script>",
        )
        self.assertIn("/#resource/subscriptions/sample/resourceGroups/lab", self.html())
        self.assertIn("/ontologies/ontology", self.html())
        self.assertNotIn("<script>", self.html())
        self.assertIn("SDK/API-only", self.html())
        with self.assertRaises(ValueError):
            visuals.show_portal_links("not-a-hostname")
        with self.assertRaises(ValueError):
            visuals.show_portal_links("https://lab.search.windows.net", search_resource_id="bad")

    def test_unknown_architecture_fails(self):
        with self.assertRaises(ValueError):
            visuals.show_architecture("not-a-stage")


if __name__ == "__main__":
    unittest.main()
