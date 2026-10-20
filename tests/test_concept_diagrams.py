"""Offline checks for the conceptual illustrations and their teaching positions."""

import ast
import importlib.util
import json
import re
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "concept_diagrams", ROOT / "scripts" / "build-concept-diagrams.py"
)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
TAG = "lab-concept-guide"


class ConceptDiagramTests(unittest.TestCase):
    def test_sources_are_deterministic_accessible_and_match_previews(self):
        diagrams = generator.build_all()
        self.assertEqual(len(diagrams), 12)
        for name, diagram in diagrams.items():
            with self.subTest(concept=name):
                svg, scene = diagram.result()
                self.assertEqual(svg, (generator.OUT / f"{name}.svg").read_text(encoding="utf-8"))
                self.assertEqual(scene, json.loads(
                    (generator.OUT / f"{name}.excalidraw").read_text(encoding="utf-8")
                ))
                root = ET.fromstring(svg)
                ns = {"s": "http://www.w3.org/2000/svg"}
                self.assertTrue(root.find("s:title", ns).text)
                self.assertTrue(root.find("s:desc", ns).text)
                self.assertNotIn("<image", svg)
                self.assertNotIn("https://", svg)
                data = (generator.OUT / f"{name}.png").read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", data[16:24]), (1440, diagram.height))
                self.assertEqual(data, generator.resvg_py.svg_to_bytes(svg_string=svg))
                for element in scene["elements"]:
                    if element["type"] != "text":
                        continue
                    self.assertEqual(element["strokeColor"], "#000000")
                    self.assertGreaterEqual(element["x"], 0)
                    self.assertLessEqual(element["x"] + element["width"], 1440)
                    lines = len(element["text"].splitlines())
                    visible_bottom = element["y"] + element["fontSize"] * 1.45 * lines
                    self.assertLessEqual(visible_bottom, diagram.height)
                    self.assertGreaterEqual(element["height"], element["fontSize"] * 2.5 * lines)

    def test_notebook_concepts_are_unique_and_precede_their_exercise(self):
        expected = {
            1: [("step2", "model-roles"), ("step3", "document-ingestion"),
                ("step4", "source-versus-kb"), ("step6", "index-anatomy"),
                ("references", "citation-trail")],
            2: [("step2", "authorization-lanes"), ("step3", "ontology-relationships")],
            3: [("step5", "workplace-versus-commitment")],
            4: [("step5", "evidence-roles")],
            5: [("step3", "answer-boundary")],
        }
        for part, guides in expected.items():
            path, = (ROOT / "src" / "notebooks").glob(f"part{part}-*.ipynb")
            notebook = json.loads(path.read_text(encoding="utf-8"))
            cells = notebook["cells"]
            concept_cells = [c for c in cells if TAG in c.get("metadata", {}).get("tags", [])]
            self.assertEqual(len(concept_cells), len(guides))
            self.assertEqual(len({c.get("id") for c in concept_cells}), len(guides))
            for anchor, image in guides:
                cell, = [c for c in concept_cells if c["id"] == f"concept-p{part}-{anchor}"]
                self.assertEqual(cell["cell_type"], "markdown")
                text = "".join(cell["source"])
                self.assertNotIn(";", text)
                self.assertNotIn("\u2014", text)
                self.assertIn("Concept illustration", text)
                target = f"../../img/concepts/{image}.png"
                self.assertIn(target, text)
                self.assertTrue((path.parent / target).is_file())
                following = "".join(cells[cells.index(cell) + 1]["source"])
                if anchor == "references":
                    self.assertTrue(following.startswith("### Review the references"))
                else:
                    step = anchor.removeprefix("step")
                    self.assertRegex(following, rf"(?m)^## Step {step}:")
            code = "\n".join(
                "".join(c["source"]) for c in cells if c["cell_type"] == "code"
            )
            compile(code, str(path), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    def test_every_concept_is_linked_and_no_guide_is_a_portal_capture(self):
        documents = [(ROOT / "src" / "notebooks" / "README.md").read_text(encoding="utf-8")]
        for path in (ROOT / "src" / "notebooks").glob("part*.ipynb"):
            for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]:
                if TAG in cell.get("metadata", {}).get("tags", []):
                    self.assertNotIn("lab-portal-capture", cell["metadata"]["tags"])
                    documents.append("".join(cell["source"]))
        links = set(re.findall(r"img/concepts/([\w-]+)\.png", "\n".join(documents)))
        self.assertEqual(links, set(generator.build_all()))


if __name__ == "__main__":
    unittest.main()
