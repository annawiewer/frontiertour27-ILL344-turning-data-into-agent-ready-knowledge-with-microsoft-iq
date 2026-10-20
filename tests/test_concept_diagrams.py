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

    def test_notebooks_keep_only_boundary_architectures_and_portal_images(self):
        for path in (ROOT / "src" / "notebooks").glob("part*.ipynb"):
            notebook = json.loads(path.read_text(encoding="utf-8"))
            cells = notebook["cells"]
            architecture_cells = []
            for index, cell in enumerate(cells):
                if cell["cell_type"] != "markdown":
                    continue
                self.assertFalse(set(cell.get("metadata", {}).get("tags", [])) & {
                    TAG, "lab-section-map", "lab-section-compare", "lab-guide-intro",
                })
                text = "".join(cell["source"])
                images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
                for target in images:
                    self.assertTrue((path.parent / target).is_file())
                    self.assertTrue(target.startswith(("../../img/architecture/", "../../img/portal/")))
                if any("/architecture/" in target for target in images):
                    architecture_cells.append(index)
            self.assertEqual(len(architecture_cells), 2, path.name)
            self.assertLessEqual(architecture_cells[0], 1)
            self.assertGreaterEqual(architecture_cells[1], len(cells) - 3)
            code = "\n".join(
                "".join(c["source"]) for c in cells if c["cell_type"] == "code"
            )
            compile(code, str(path), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    def test_every_concept_remains_available_in_companion_material(self):
        documents = [
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in ("src/notebooks/README.md", "docs/visual-guide.md")
        ]
        links = set(re.findall(r"img/concepts/([\w-]+)\.png", "\n".join(documents)))
        self.assertEqual(links, set(generator.build_all()))


if __name__ == "__main__":
    unittest.main()
