"""Static checks, with no notebook execution or cloud access."""

import ast
import builtins
import hashlib
import importlib.util
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "src" / "notebooks"


class NotebookGuideTests(unittest.TestCase):
    def test_notebooks_compile_have_guides_and_keep_mission_structure(self):
        paths = sorted(NOTEBOOKS.glob("part*.ipynb"))
        self.assertEqual(len(paths), 5)
        for path in paths:
            with self.subTest(notebook=path.name):
                nb = json.loads(path.read_text(encoding="utf-8"))
                cells = nb["cells"]
                self.assertIn("Mission", "".join(cells[0]["source"]))
                self.assertIn("## \u2705 Mission complete", "".join(cells[-2]["source"]))
                self.assertIn("Continue", "".join(cells[-1]["source"]))
                ids = [c["id"] for c in cells if "id" in c]
                self.assertEqual(len(ids), len(set(ids)))
                code = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
                compile(code, str(path), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
                # Parts 1 and 2 retain their original raw evidence displays.
                if not path.name.startswith(("part1", "part2")):
                    self.assertIn("show_portal_links(", code)
                    self.assertIn("verify_knowledge_base(", code)
                    self.assertLess(code.index("from lab_visuals import"), code.index("show_portal_links("))
                    if not path.name.startswith("part5"):
                        self.assertIn("show_activity(activities_json)", code)
                        self.assertIn("show_references(references_json", code)
                else:
                    self.assertIn("print(json.dumps(activities_json", code)
                    self.assertIn("print(json.dumps(references_json", code)
                for c in cells:
                    if c["cell_type"] == "code":
                        # Executed working copies are allowed. Clear outputs before committing.
                        count = c["execution_count"]
                        self.assertTrue(count is None or isinstance(count, int) and count > 0)
                        if count is None:
                            self.assertEqual(c["outputs"], [])
                        self.assertFalse(any(o["output_type"] == "error" for o in c["outputs"]))
                    if set(c.get("metadata", {}).get("tags", [])) & {
                        "lab-visual-guide", "lab-section-map", "lab-section-compare", "lab-guide-intro",
                        "lab-portal-capture", "lab-concept-guide",
                    }:
                        source = "".join(c["source"])
                        if c["cell_type"] == "markdown":
                            self.assertNotIn("\u2014", source)
                            self.assertNotIn(";", source)

    def test_new_markdown_links_resolve(self):
        documents = [
            (path, "\n".join("".join(c["source"]) for c in json.loads(
                path.read_text(encoding="utf-8")
            )["cells"] if set(c.get("metadata", {}).get("tags", [])) & {
                "lab-visual-guide", "lab-section-map", "lab-section-compare", "lab-guide-intro",
                "lab-portal-capture", "lab-concept-guide",
            }))
            for path in NOTEBOOKS.glob("part*.ipynb")
        ]
        documents += [(ROOT / p, (ROOT / p).read_text(encoding="utf-8")) for p in (
            "README.md", "docs/visual-guide.md", "docs/README.md", "src/README.md",
            "src/notebooks/README.md", "instructions/summary.md"
        )]
        for path, text in documents:
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(document=path.name, target=target):
                    self.assertTrue((path.parent / unquote(target.split("#")[0])).exists())

    def test_generated_diagrams_match_sources_and_fit_canvas(self):
        script = ROOT / "scripts" / "build-lab-diagrams.py"
        spec = importlib.util.spec_from_file_location("lab_diagrams", script)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        diagrams = [(stage, generator.build(stage)) for stage in generator.STAGES]
        diagrams += [("overview", generator.build_overview())]
        diagrams += [(f"step-{key}", generator.build_flow(key)) for key in generator.FLOWS]
        self.assertEqual(len(diagrams), 24)
        for stage, (svg, scene) in diagrams:
            with self.subTest(stage=stage):
                self.assertEqual(svg, (generator.OUT / f"{stage}.svg").read_text(encoding="utf-8"))
                self.assertEqual(scene, json.loads(
                    (generator.OUT / f"{stage}.excalidraw").read_text(encoding="utf-8")
                ))
                root = ET.fromstring(svg)
                height = int(root.attrib["height"])
                rectangles = {e["id"]: e for e in scene["elements"] if e["type"] == "rectangle"}
                for element in scene["elements"]:
                    if element["type"] == "text":
                        self.assertEqual(element["strokeColor"], "#000000")
                        self.assertLessEqual(element["x"] + element["width"], 1560)
                        self.assertLessEqual(element["y"] + element["height"], height)
                        if element["id"].endswith("-text"):
                            card = rectangles[element["id"].removesuffix("-text")]
                            self.assertLessEqual(element["x"] + element["width"], card["x"] + card["width"])
                            rendered_height = element["fontSize"] * element["lineHeight"] * len(element["text"].splitlines())
                            self.assertLessEqual(element["y"] + rendered_height, card["y"] + card["height"])
                    if stage in generator.STAGES and element["id"] in ("cloud", "local", "legend"):
                        self.assertEqual(element["backgroundColor"], "transparent")

    def test_numbered_sections_do_not_repeat_maps_or_product_comparisons(self):
        for path in sorted(NOTEBOOKS.glob("part*.ipynb")):
            cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
            steps = []
            maps = []
            comparisons = []
            for i, cell in enumerate(cells):
                text = "".join(cell["source"])
                tags = cell.get("metadata", {}).get("tags", [])
                if cell["cell_type"] == "markdown" and re.search(r"^## Step \d+:", text, re.MULTILINE):
                    steps.append(i)
                if "lab-section-map" in tags:
                    maps.append(i)
                    self.assertIn("../../img/architecture/step-", text)
                    self.assertIn("<summary>Azure service architecture", text)
                    self.assertIn("../../img/architecture/azure-", text)
                    self.assertIn("**Architecture in brief:**", text)
                    self.assertIn("**Step by step:**", text)
                    self.assertRegex(text, r"\n1\. .+\n2\. ")
                if "lab-section-compare" in tags:
                    comparisons.append(i)
                    for phrase in ("Expected after this section", "Where to look", "What to verify"):
                        self.assertIn(phrase, text)
            with self.subTest(notebook=path.name):
                self.assertTrue(steps)
                self.assertEqual(maps, [])
                self.assertEqual(comparisons, [])

    def test_added_display_cells_only_use_previously_defined_names(self):
        for path in sorted(NOTEBOOKS.glob("part*.ipynb")):
            cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
            defined = set(dir(builtins))
            for cell in cells:
                if cell["cell_type"] != "code":
                    continue
                tree = ast.parse("".join(cell["source"]))
                imports = {
                    alias.asname or alias.name.split(".")[0]
                    for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                    for alias in node.names
                }
                if cell.get("id", "").startswith("part2-visual-"):
                    loaded = {
                        node.id for node in ast.walk(tree)
                        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                    }
                    with self.subTest(notebook=path.name, cell=cell["id"]):
                        self.assertFalse(loaded - defined - imports)
                defined |= imports | {
                    node.id for node in ast.walk(tree)
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                }


class PortalCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = ROOT / "img" / "portal"
        cls.manifest = json.loads(
            (cls.directory / "captures.json").read_text(encoding="utf-8")
        )

    def test_only_documented_original_portal_images_are_published(self):
        captures = self.manifest["captures"]
        self.assertEqual(len(captures), 12)
        self.assertEqual(len({capture["id"] for capture in captures}), 12)
        self.assertEqual(
            {path.name for path in self.directory.glob("*.png")},
            {capture["file"] for capture in captures},
        )
        for capture in captures:
            with self.subTest(capture=capture["id"]):
                self.assertEqual(capture["kind"], "azure-portal")
                self.assertEqual(capture["captured_on"], self.manifest["capture_date"])
                self.assertTrue(capture["navigation"].startswith("Azure portal > "))
                self.assertTrue(capture["observed"])
                self.assertIn("masked in gray", capture["editing"])
                self.assertRegex(capture["original_sha256"], r"^[0-9a-f]{64}$")
                image = (self.directory / capture["file"]).read_bytes()
                self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(
                    hashlib.sha256(image).hexdigest(), capture["published_sha256"]
                )
                self.assertLess(len(image), 512_000)
                self.assertGreaterEqual(int.from_bytes(image[16:20], "big"), 800)

    def test_guides_match_step_coverage_and_do_not_fill_omitted_steps(self):
        coverage = self.manifest["coverage"]
        self.assertEqual(len(coverage), 31)
        self.assertEqual(sum(row["status"] == "captured" for row in coverage), 12)
        by_step = {(row["notebook"], row["step"]): row for row in coverage}
        self.assertEqual(len(by_step), 31)
        seen = set()
        used = set()
        for path in sorted(NOTEBOOKS.glob("part*.ipynb")):
            cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
            step = None
            for cell in cells:
                if cell["cell_type"] != "markdown":
                    continue
                text = "".join(cell["source"])
                match = re.search(r"^## Step (\d+):", text, re.MULTILINE)
                if match:
                    step = int(match[1])
                    self.assertIn((path.name, step), by_step)
                if "lab-portal-capture" not in cell.get("metadata", {}).get("tags", []):
                    continue
                key = (path.name, step)
                self.assertNotIn(key, seen)
                seen.add(key)
                row = by_step[key]
                self.assertEqual(row["status"], "captured")
                images = set(re.findall(r"!\[[^\]]+\]\(\.\./\.\./img/portal/([^)]+)\.png\)", text))
                self.assertEqual(images, set(row["captures"]))
                used |= images
                for phrase in ("**Open:**", "**Look for:**", "**How to read this:**",
                               self.manifest["capture_date"], "Gray blocks", "Orange outlines"):
                    self.assertIn(phrase, text)
                self.assertNotIn(";", text)
                self.assertNotIn("\u2014", text)
        self.assertEqual(seen, {
            (row["notebook"], row["step"]) for row in coverage if row["captures"]
        })
        self.assertEqual(used, {capture["id"] for capture in self.manifest["captures"]})
        for row in coverage:
            if row["status"] == "omitted":
                self.assertEqual(row["captures"], [])
                self.assertNotIn((row["notebook"], row["step"]), seen)

    def test_part1_policy_screenshot_is_shown_only_after_upload(self):
        notebook = json.loads(
            (NOTEBOOKS / "part1-standard-foundry-iq-kb.ipynb").read_text(encoding="utf-8")
        )
        image_cells = [
            cell["id"] for cell in notebook["cells"]
            if re.search(
                r"!\[[^\]]+\]\(\.\./\.\./img/portal/policy-source-files\.png\)",
                "".join(cell["source"]),
            )
        ]
        self.assertEqual(image_cells, ["part1-portal-step3"])
        navigation = next(
            cell for cell in notebook["cells"] if cell.get("id") == "part1-portal-step2"
        )
        self.assertIn("**Open:**", "".join(navigation["source"]))
        self.assertIn("Step 3", "".join(navigation["source"]))

    def test_portal_screenshots_are_not_repeated_within_a_notebook(self):
        for path in sorted(NOTEBOOKS.glob("part*.ipynb")):
            notebook = json.loads(path.read_text(encoding="utf-8"))
            seen = {}
            for cell in notebook["cells"]:
                if cell["cell_type"] != "markdown":
                    continue
                for filename in re.findall(
                    r"!\[[^\]]*\]\(\.\./\.\./img/portal/([^)]+\.png)\)",
                    "".join(cell["source"]),
                ):
                    digest = hashlib.sha256(
                        (self.directory / filename).read_bytes()
                    ).hexdigest()
                    with self.subTest(notebook=path.name, image=filename):
                        self.assertNotIn(
                            digest, seen,
                            f"{filename} repeats the screenshot from cell {seen.get(digest)}",
                        )
                    seen[digest] = cell.get("id")

    def test_manifest_does_not_publish_environment_identifiers(self):
        text = json.dumps(self.manifest)
        self.assertNotRegex(text, r"(?i)\.onmicrosoft\.com|/subscriptions/|C:\\\\Users\\\\")
        self.assertNotRegex(
            text,
            r"(?i)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        )
        self.assertIn("No simulated portal", self.manifest["policy"])


class AzureArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "azure_diagrams", ROOT / "scripts" / "build-azure-architecture.py"
        )
        cls.generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.generator)

    def test_official_icon_provenance_and_branding(self):
        manifest = self.generator.check_icons()
        self.assertEqual(len(manifest["icons"]), 7)

    def test_part1_before_and_after_reveal_only_the_current_build(self):
        ns = "{http://www.w3.org/2000/svg}"
        notebook = json.loads(
            (NOTEBOOKS / "part1-standard-foundry-iq-kb.ipynb").read_text(encoding="utf-8")
        )
        markdown = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown"]
        for complete, name in ((False, "part1-before"), (True, "part1-after")):
            with self.subTest(complete=complete):
                svg = self.generator.build_part1_reveal(complete)
                self.assertEqual(svg, (self.generator.OUT / f"{name}.svg").read_text(encoding="utf-8"))
                root = ET.fromstring(svg)
                groups = {
                    group.find(ns + "title").text: group
                    for group in root.iter(ns + "g")
                    if group.find(ns + "title") is not None
                }
                self.assertEqual(len(root.findall(f".//{ns}g[@data-part1-cover]")), 2)
                self.assertEqual(groups["models"].attrib["opacity"], "0.55")
                self.assertEqual(groups["entra"].attrib["opacity"], "0.18")
                for node in ("kb", "policy", "indexes") if complete else ("kb", "policy"):
                    self.assertEqual(groups[node].find(ns + "path").attrib["stroke"], self.generator.ORANGE)
                if not complete:
                    self.assertEqual(groups["indexes"].attrib["opacity"], "0.12")
                caption = next(text for text in markdown if "Architecture recap: what Part 1 created" in text) if complete else markdown[0]
                self.assertIn(f"../../img/architecture/{name}.png", caption)
                png = (self.generator.OUT / f"{name}.png").read_bytes()
                self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(int.from_bytes(png[16:20], "big"), 1800)

    def test_parts_2_to_5_have_distinct_planned_and_completed_architectures(self):
        ns = "{http://www.w3.org/2000/svg}"
        for part, config in self.generator.PART_REVEALS.items():
            path, = NOTEBOOKS.glob(f"part{part}-*.ipynb")
            notebook = json.loads(path.read_text(encoding="utf-8"))
            markdown = "\n".join(
                "".join(cell["source"]) for cell in notebook["cells"]
                if cell["cell_type"] == "markdown"
            )
            images = []
            for complete, suffix in ((False, "before"), (True, "after")):
                name = f"part{part}-{suffix}"
                with self.subTest(part=part, complete=complete):
                    svg = self.generator.build_part_reveal(part, complete)
                    self.assertEqual(
                        svg, (self.generator.OUT / f"{name}.svg").read_text(encoding="utf-8")
                    )
                    root = ET.fromstring(svg)
                    text = " ".join(root.itertext())
                    self.assertIn("Faded: existing / background" if part in (4, 5)
                                  else "Faded: reused", text)
                    self.assertNotIn("Gray boxes: not connected", text)
                    membership = "connected" if complete else "planned"
                    source_kind = "references" if part in (4, 5) else "definitions"
                    if part == 5:
                        self.assertIn("three Part 1 sources", text)
                    else:
                        self.assertIn(f"{membership} source {source_kind}", text)
                    groups = {
                        group.find(ns + "title").text: group
                        for group in root.iter(ns + "g")
                        if group.find(ns + "title") is not None
                    }
                    self.assertEqual(
                        {g.attrib["data-part-cover"]
                         for g in root.findall(f".//{ns}g[@data-part-cover]")},
                        set(config["covers"]),
                    )
                    for node in config["focus"]:
                        self.assertEqual(groups[node].attrib["opacity"], "1")
                        self.assertEqual(groups[node].attrib["data-build-state"],
                                         "completed" if complete else "planned")
                        shape = groups[node].find(ns + "path")
                        self.assertEqual(shape.attrib["stroke"], self.generator.ORANGE)
                        self.assertEqual("stroke-dasharray" in shape.attrib, not complete)
                    for edge in config["new_edges"]:
                        self.assertEqual(groups[edge].attrib["opacity"], "1" if complete else "0.12")
                    for node in ("policy", "indexes", "models"):
                        self.assertEqual(groups[node].attrib["opacity"], "0.55")
                    for node in ("cluster_identity", "entra", "notebook->entra"):
                        if part == 5:
                            self.assertNotIn(node, groups)
                        else:
                            self.assertEqual(groups[node].attrib["opacity"], "0.18")
                    for node in ("cluster_foundry", "cluster_azure", "cluster_local"):
                        self.assertEqual(groups[node].attrib["opacity"], "0.55")
                    for node in ("policy", "indexes"):
                        self.assertEqual(groups[node].find(ns + "path").attrib["stroke"].lower(),
                                         self.generator.BLUE.lower())
                    if part == 5:
                        self.assertNotIn("kb->models", groups)
                        self.assertIn("agent->models", groups)
                    self.assertIn(f"../../img/architecture/{name}.png", markdown)
                    self.assertNotIn(f"../../img/architecture/azure-{config['stage']}.png", markdown)
                    png = (self.generator.OUT / f"{name}.png").read_bytes()
                    self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
                    self.assertEqual(int.from_bytes(png[16:20], "big"), 1800)
                    images.append(png)
            self.assertNotEqual(*images)

    def test_part4_separates_updated_search_definitions_from_existing_data(self):
        ns = "{http://www.w3.org/2000/svg}"
        for complete in (False, True):
            root = ET.fromstring(self.generator.build_part_reveal(4, complete))
            groups = {
                group.find(ns + "title").text: group
                for group in root.iter(ns + "g")
                if group.find(ns + "title") is not None
            }
            for node in ("index_sources", "fabric_source", "workiq_source", "kb"):
                self.assertEqual(groups[node].attrib["data-build-state"],
                                 "completed" if complete else "planned")
            for node in ("indexes", "policy", "ontology", "lakehouse", "workiq"):
                self.assertEqual(groups[node].attrib["opacity"], "0.55")
                self.assertEqual(groups[node].find(ns + "path").attrib["stroke"].lower(),
                                 self.generator.BLUE.lower())
                self.assertNotIn("data-build-state", groups[node].attrib)
            for edge in ("kb->index_sources", "index_sources->indexes", "kb->fabric_source",
                         "fabric_source->ontology", "kb->workiq_source", "workiq_source->workiq"):
                self.assertIn(edge, groups)
            self.assertNotIn("pdf", groups)
            self.assertNotIn("policy->models", groups)

    def test_part5_explains_agent_model_and_evidence_without_sdk_boxes(self):
        ns = "{http://www.w3.org/2000/svg}"
        for complete in (False, True):
            root = ET.fromstring(self.generator.build_part_reveal(5, complete))
            text = " ".join(root.itertext())
            groups = {
                group.find(ns + "title").text: group
                for group in root.iter(ns + "g")
                if group.find(ns + "title") is not None
            }
            for edge in ("notebook->agent", "agent->models", "agent->kb",
                         "kb->policy", "kb->indexes"):
                self.assertEqual(groups[edge].attrib["opacity"], "1" if complete else "0.12")
            for omitted in ("kb->models", "notebook->kb", "notebook->entra", "pdf",
                            "ontology", "workiq", "policy->models", "mcp_tool",
                            "mcp_endpoint", "index_sources"):
                self.assertNotIn(omitted, groups)
            self.assertNotIn("opacity", groups["notebook"].attrib)
            for phrase in ("Your question and answer", "Python code running in your notebook",
                           "MCP: get evidence", "No model attached",
                           "Returns evidence, not a written answer",
                           "Turns retrieved evidence into an answer"):
                self.assertIn(phrase, text)
            nodes = {name for name, group in groups.items() if group.attrib.get("class") == "node"}
            self.assertEqual(nodes, {"notebook", "agent", "kb", "models", "policy", "indexes"})
            self.assertNotIn("Other parts: reference only", text)
            self.assertNotIn("The agent calls the model, not the KB", text)

    def test_shared_descriptions_match_diagrams_and_notebook_captions(self):
        descriptions = json.loads(
            (self.generator.OUT / "descriptions.json").read_text(encoding="utf-8")
        )
        self.assertEqual(descriptions, {
            stage: " ".join(lines) for stage, lines in self.generator.DESCRIPTIONS.items()
        })
        for stage, sentences in self.generator.DESCRIPTIONS.items():
            svg = ET.fromstring(
                (self.generator.OUT / f"azure-{stage}.svg").read_text(encoding="utf-8")
            )
            text = "".join(svg.itertext())
            for sentence in sentences:
                self.assertIn(sentence, text)

    def test_visible_color_legend_and_shared_numbered_walkthroughs(self):
        ns = "{http://www.w3.org/2000/svg}"
        walkthroughs = json.loads(
            (self.generator.OUT / "walkthroughs.json").read_text(encoding="utf-8")
        )
        self.assertEqual(walkthroughs, self.generator.WALKTHROUGHS)
        self.assertEqual(set(walkthroughs), {"overview", *self.generator.STAGES})
        for stage, steps in walkthroughs.items():
            with self.subTest(stage=stage):
                self.assertGreaterEqual(len(steps), 5)
                self.assertTrue(all(";" not in step and "\u2014" not in step for step in steps))
                svg = ET.fromstring(
                    (self.generator.OUT / f"azure-{stage}.svg").read_text(encoding="utf-8")
                )
                text = "".join(svg.itertext())
                self.assertIn("Arrow and object legend", text)
                for color, phrase in (
                    (self.generator.BLUE, "Blue, solid:"),
                    (self.generator.PURPLE, "Purple, solid:"),
                    (self.generator.GRAY, "Gray, dashed:"),
                    (self.generator.ORANGE, "Orange boxes:"),
                ):
                    self.assertIn(phrase, text)
                    samples = [
                        node.text for node in svg.iter(ns + "text")
                        if node.attrib.get("fill", "").lower() == color.lower()
                    ]
                    self.assertTrue(any("\u25b6" in sample or "\u25a0" in sample for sample in samples))
        for path in NOTEBOOKS.glob("part*.ipynb"):
            for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]:
                if cell["cell_type"] != "markdown":
                    continue
                text = "".join(cell["source"])
                for stage in re.findall(r"img/architecture/azure-(\w+)\.svg\)", text):
                    self.assertIn("**Step by step:**", text)
                    for number, step in enumerate(walkthroughs[stage], 1):
                        self.assertIn(f"{number}. {step}", text)
        for relative in ("README.md", "src/README.md", "src/notebooks/README.md", "docs/visual-guide.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            for stage in re.findall(r"!\[[^\]]*\]\([^)\n]*img/architecture/azure-(\w+)\.svg\)", text):
                for number, step in enumerate(walkthroughs[stage], 1):
                    self.assertIn(f"{number}. {step}", text)

    def test_connections_are_thick_orthogonal_and_do_not_cut_through_other_nodes(self):
        ns = "{http://www.w3.org/2000/svg}"

        def points(path):
            numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.attrib["d"])]
            return list(zip(numbers[::2], numbers[1::2]))

        for stage in ("overview", *self.generator.STAGES, "part4-before", "part4-after",
                      "part5-before", "part5-after"):
            filename = stage if stage.startswith("part") else f"azure-{stage}"
            svg = ET.fromstring(
                (self.generator.OUT / f"{filename}.svg").read_text(encoding="utf-8")
            )
            nodes = {}
            edges = []
            for group in svg.iter(ns + "g"):
                if group.attrib.get("class") == "node":
                    coordinates = points(group.find(ns + "path"))
                    nodes[group.find(ns + "title").text] = (
                        min(x for x, _ in coordinates), min(y for _, y in coordinates),
                        max(x for x, _ in coordinates), max(y for _, y in coordinates),
                    )
                elif group.attrib.get("class") == "edge":
                    edges.append(group)
            by_name = {edge.find(ns + "title").text: edge for edge in edges}
            if "kb->models" in by_name:
                model_path = by_name["kb->models"].findall(".//" + ns + "path")[-1]
                input_path = by_name["notebook->kb"].findall(".//" + ns + "path")[-1]
                self.assertGreater(
                    abs(points(model_path)[0][1] - points(input_path)[-1][1]), 16,
                    f"{stage}: model call overlaps the notebook retrieval connection",
                )
            for edge in edges:
                name = edge.find(ns + "title").text
                endpoints = name.split("->")
                paths = edge.findall(".//" + ns + "path")
                with self.subTest(stage=stage, edge=name):
                    self.assertEqual(len(paths), 2)
                    casing, path = paths
                    self.assertEqual(casing.attrib["stroke"], "white")
                    self.assertGreaterEqual(float(path.attrib["stroke-width"]), 3)
                    self.assertEqual(casing.attrib["d"], path.attrib["d"])
                    coordinates = points(path)
                    for (x1, y1), (x2, y2) in zip(coordinates, coordinates[1:]):
                        self.assertTrue(abs(x1 - x2) < .01 or abs(y1 - y2) < .01)
                        for node, (left, top, right, bottom) in nodes.items():
                            if node in endpoints:
                                continue
                            crosses = (
                                left + 1 < x1 < right - 1
                                and max(min(y1, y2), top + 1) < min(max(y1, y2), bottom - 1)
                                if abs(x1 - x2) < .01 else
                                top + 1 < y1 < bottom - 1
                                and max(min(x1, x2), left + 1) < min(max(x1, x2), right - 1)
                            )
                            self.assertFalse(crosses, f"{stage}: {name} crosses {node}")

    def test_eight_generated_architectures_are_self_contained_and_current(self):
        for stage in ("overview", *self.generator.STAGES):
            with self.subTest(stage=stage):
                base = self.generator.OUT / f"azure-{stage}"
                self.assertEqual(
                    base.with_suffix(".dot").read_text(encoding="utf-8"),
                    self.generator.build(stage),
                )
                svg = ET.fromstring(base.with_suffix(".svg").read_text(encoding="utf-8"))
                self.assertEqual(svg.attrib["role"], "img")
                self.assertIn("not a live deployment status", svg.attrib["aria-label"])
                images = svg.findall(".//{http://www.w3.org/2000/svg}image")
                self.assertGreaterEqual(len(images), 5)
                for image in images:
                    self.assertTrue(image.attrib["{http://www.w3.org/1999/xlink}href"].startswith(
                        "data:image/svg+xml;base64,"
                    ))
                png = base.with_suffix(".png").read_bytes()
                self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(int.from_bytes(png[16:20], "big"), 1800)
                self.assertGreater(int.from_bytes(png[20:24], "big"), 0)

    def test_source_branches_and_local_agent_synthesis_boundary(self):
        for stage, expected in (
            ("start", set()), ("policy", {"policy"}),
            ("documents", {"policy", "indexes"}),
            ("fabric", {"policy", "indexes", "ontology"}),
            ("workiq", {"policy", "indexes", "workiq"}),
            ("combined", {"policy", "indexes", "ontology", "workiq"}),
            ("agent", {"policy", "indexes"}),
        ):
            with self.subTest(stage=stage):
                source = self.generator.build(stage)
                visible = [
                    line for line in source.splitlines()
                    if " -> " in line and "style=invis" not in line
                ]
                retrieval = {
                    target for target in ("policy", "indexes", "ontology", "workiq")
                    if any(line.startswith(f"kb -> {target} ") for line in visible)
                }
                self.assertEqual(retrieval, expected)
                self.assertEqual(any(line.startswith("kb -> models ") for line in visible),
                                 stage not in {"start", "agent"})
                self.assertEqual(any(line.startswith("agent -> models ") for line in visible),
                                 stage == "agent")
                for boundary in ("cluster_local", "cluster_azure", "cluster_fabric",
                                 "cluster_m365", "cluster_identity"):
                    self.assertIn(boundary, source)
        agent = self.generator.build("agent")
        self.assertIn("knowledge_base_retrieve", agent)
        self.assertIn("extractiveData / minimal / no model", agent)
        self.assertIn("Not a hosted Foundry agent", agent)


if __name__ == "__main__":
    unittest.main()
