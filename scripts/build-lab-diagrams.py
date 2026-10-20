"""Generate matching SVG and editable Excalidraw architecture guides, offline."""

import json
import textwrap
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "architecture"
SOURCES = [
    ("policy", "Purchasing policy", "CAL-POL-PUR-001.pdf", "File source created in Part 1"),
    ("evidence", "Supplier evidence", "supplier-evidence", "Preloaded index, source added in Part 1"),
    ("sourcing", "Approved commitments", "sourcing-documents", "Preloaded index, source added in Part 1"),
    ("fabric", "Structured relationships", "CaldovaMedicinalProductOntology", "Preconfigured Fabric, live source in Part 2"),
    ("workiq", "Workplace discussion", "Work IQ / Microsoft 365", "Preconfigured identity, live source in Part 3"),
]
BASE = {"policy", "evidence", "sourcing"}
STAGES = {
    "start": ("Your preconfigured foundation", "No attendee knowledge base yet", set(), set()),
    "policy": ("Part 1A: ingest and query purchasing policy", "caldova-policy-knowledge-base", {"policy"}, {"policy"}),
    "documents": ("Part 1B: connect three evidence sources", "caldova-supply-chain-knowledge-base", BASE, {"evidence", "sourcing"}),
    "fabric": ("Part 2: add structured Fabric relationships", "caldova-fabric-knowledge-base", BASE | {"fabric"}, {"fabric"}),
    "workiq": ("Part 3: add current workplace context", "caldova-workiq-knowledge-base", BASE | {"workiq"}, {"workiq"}),
    "combined": ("Part 4: combine five sources", "caldova-supply-chain-briefing-knowledge-base", BASE | {"fabric", "workiq"}, {"fabric", "workiq"}),
    "agent": ("Part 5: move answer synthesis to a local agent", "caldova-supply-chain-minimal-knowledge-base", BASE, set()),
}

FLOWS = {
    "configuration": (
        "Connect the notebook to existing services",
        [
            ("LOCAL | .env", "Endpoints and deployment names", "Keep credentials private"),
            ("LOCAL | Python notebook", "Load configuration", "No deployment in this step"),
            ("CLOUD | Existing services", "Search and Azure OpenAI", "Fabric / identity when needed"),
            ("CHECK | Your environment", "Correct tenant and resource", "Never screenshot credentials"),
        ], 1,
    ),
    "file-source": (
        "Define a file source before uploading content",
        [
            ("LOCAL | Policy PDF", "CAL-POL-PUR-001.pdf", "Not uploaded in this step"),
            ("SEARCH | File source", "Create the source definition", "Attach embedding configuration"),
            ("OPENAI | Embedding model", "text-embedding-3-large", "Existing model deployment"),
            ("CHECK | Source definition", "Kind: file", "No queryable policy yet"),
        ], 1,
    ),
    "ingestion": (
        "Turn the policy file into searchable content",
        [
            ("LOCAL | Policy PDF", "Upload the purchasing policy", "One source document"),
            ("SEARCH | File ingestion", "Extract and chunk text", "Generate embeddings"),
            ("SEARCH | Searchable content", "Store chunks and vectors", "Processing can take time"),
            ("CHECK | Ingestion status", "Read back files and errors", "Later verify a file citation"),
        ], 1,
    ),
    "policy-query": (
        "Retrieve policy evidence and synthesize a cited answer",
        [
            ("LOCAL | Question", "Ask about purchasing policy", "Call the Search retrieve API"),
            ("SEARCH | Policy KB", "One file knowledge source", "Retrieve policy evidence"),
            ("OPENAI | Attached model", "Plan retrieval and synthesize", "Runs through the KB"),
            ("LOCAL | Answer and evidence", "Inspect activity and references", "Match citations to claims"),
        ], 1,
    ),
    "indexes": (
        "Connect existing indexes without reingesting documents",
        [
            ("SEARCH | Preloaded indexes", "supplier-evidence", "sourcing-documents"),
            ("SEARCH | Two source definitions", "Point to the existing indexes", "Keep citation metadata"),
            ("SEARCH | Three-source KB", "Policy plus two index sources", "Create a separate KB variant"),
            ("CHECK | Exact membership", "Three connected sources", "No Fabric or Work IQ here"),
        ], 1,
    ),
    "documents-query": (
        "Keep policy, approved commitments and operational facts distinct",
        [
            ("LOCAL | Shipment question", "What happened?", "May the units be distributed?"),
            ("SEARCH | Three-source KB", "Policy and indexed evidence", "Sources can be skipped per query"),
            ("OPENAI | Attached model", "Synthesize from retrieved facts", "Do not invent missing evidence"),
            ("LOCAL | Answer and evidence", "Match reference IDs to claims", "Inspect actual source activity"),
        ], 1,
    ),
    "fabric-auth": (
        "Authorize live Fabric retrieval as the signed-in user",
        [
            ("USER | Fabric-enabled account", "Use the intended tenant", "Workspace access is required"),
            ("ENTRA | Delegated token", "Search audience", "Not the Search admin key"),
            ("LOCAL | Retrieval request", "Pass query-source authorization", "Keep the token private"),
            ("FABRIC | Source access", "Read permitted ontology facts", "Not a bulk copy into Search"),
        ], 1,
    ),
    "fabric-source": (
        "Add a live ontology connection, not a new Fabric deployment",
        [
            ("FABRIC | Existing ontology", "Manufacturer > substance", "Substance > medicinal product"),
            ("SEARCH | Fabric source", "Reference workspace and ontology", "Create a connection definition"),
            ("SEARCH | Separate Fabric KB", "Three Part 1 sources + Fabric", "Four sources in this variant"),
            ("CHECK | Query evidence", "fabricOntology activity", "Inspect fabricRawData"),
        ], 1,
    ),
    "workiq-auth": (
        "Authorize workplace retrieval without exposing user context",
        [
            ("ENTRA | Existing lab app", "Exposed access_as_user scope", "Federated credential configured"),
            ("USER | Interactive sign-in", "Acquire a Work IQ assertion", "Use the intended M365 tenant"),
            ("LOCAL | Retrieval request", "Pass Work IQ authorization", "Never display the assertion"),
            ("M365 | Work IQ access", "Respect the user's permissions", "Workplace context stays remote"),
        ], 1,
    ),
    "workiq-source": (
        "Add workplace discussion alongside approved commitments",
        [
            ("M365 | Existing work context", "Current actions and decisions", "Not contractual approval"),
            ("SEARCH | Work IQ source", "App and federation references", "SDK/API configuration in preview"),
            ("SEARCH | Separate Work IQ KB", "Three Part 1 sources + Work IQ", "Four sources, without Fabric"),
            ("CHECK | Query evidence", "workIQ activity and citations", "Inspect the linked source items"),
        ], 1,
    ),
    "combined-auth": (
        "Supply both authorization contexts for the combined query",
        [
            ("USER | Intended lab identity", "Fabric workspace permissions", "Microsoft 365 permissions"),
            ("ENTRA | Two token contexts", "Fabric delegated token", "Work IQ user assertion"),
            ("LOCAL | Retrieval request", "Pass each to its own parameter", "No credentials in diagrams"),
            ("REMOTE | Permission checks", "Fabric and Work IQ", "Access can fail independently"),
        ], 1,
    ),
    "combined-query": (
        "Combine five evidence roles without merging their authority",
        [
            ("SOURCES | Three document roles", "Policy / operational evidence", "Approved sourcing commitments"),
            ("LIVE | Two remote sources", "Fabric relationships", "Work IQ workplace discussion"),
            ("SEARCH | Combined KB", "Five source references", "Attached model synthesizes"),
            ("LOCAL | Supply-chain briefing", "Inspect calls and citations", "A configured source may not run"),
        ], 2,
    ),
    "agent-auth": (
        "Authenticate MCP calls without publishing the key",
        [
            ("LOCAL | Lab configuration", "Search admin key", "Keep it out of screenshots"),
            ("LOCAL | Header provider", "Add api-key to MCP requests", "Lab authentication pattern"),
            ("SEARCH | MCP endpoint", "Authenticate the request", "No new endpoint deployment"),
            ("CHECK | Safe inspection", "Inspect KB name and tool name", "Never print the header values"),
        ], 1,
    ),
    "agent-kb": (
        "Create model-free retrieval for the local agent",
        [
            ("SOURCES | Part 1 only", "Policy and two index sources", "No Fabric or Work IQ"),
            ("SEARCH | Extractive KB", "extractiveData / minimal", "No attached model"),
            ("MCP | Existing KB endpoint", "knowledge_base_retrieve", "Return evidence, not an answer"),
            ("LOCAL | Agent boundary", "The agent will synthesize", "Azure OpenAI is called separately"),
        ], 1,
    ),
    "agent-run": (
        "Run an agent locally instead of deploying a hosted agent",
        [
            ("LOCAL | Agent Framework", "Receive the user's question", "Python process in this notebook"),
            ("MCP | Tool call", "knowledge_base_retrieve", "Read extracts from Part 1 sources"),
            ("OPENAI | Agent's model", "Use the retrieved evidence", "Synthesize the final answer"),
            ("LOCAL | Answer and tool trace", "Inspect messages and citations", "No hosted Foundry agent created"),
        ], 0,
    ),
    "evidence": (
        "Prove what happened, not just what was configured",
        [
            ("RESULT | Answer", "Identify a supported claim", "An answer alone is not proof"),
            ("TRACE | Source activity", "Was the source actually called?", "Check errors and warnings"),
            ("REFERENCES | Returned evidence", "Match activitySource to id", "Check titles and citation targets"),
            ("CHECK | Evidence boundary", "Configured / called / cited", "These are different observations"),
        ], 1,
    ),
}


def _map(title, subtitle, nodes, edges, notes, height):
    """Render the same positioned elements to SVG and an editable scene."""
    elements = []
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="{height}" '
        f'viewBox="0 0 1560 {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
        f'<rect width="1560" height="{height}" fill="#ffffff"/>',
    ]

    def label(id_, x, y, lines, size=18):
        text = "\n".join(lines)
        elements.append({
            "id": id_, "type": "text", "x": x, "y": y,
            "width": max(map(len, lines)) * size * 0.63,
            "height": size * 2.5 * len(lines), "text": text, "originalText": text,
            "fontSize": size, "fontFamily": 2, "strokeColor": "#000000",
            "backgroundColor": "transparent", "textAlign": "left", "verticalAlign": "top",
            "lineHeight": 1.5, "angle": 0, "roughness": 0, "seed": len(elements) + 1,
            "version": 1, "versionNonce": 1, "isDeleted": False,
            "groupIds": [], "boundElements": None, "containerId": None,
        })
        spans = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.5}">{escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        svg.append(
            f'<text x="{x}" y="{y + size}" fill="#000000" font-size="{size}" '
            f'font-family="Segoe UI,Arial,sans-serif">{spans}</text>'
        )

    label("heading", 30, 12, [title], 26)
    label("subtitle", 30, 58, [subtitle], 16)
    for id_, x, y, w, h, lines, focus in nodes:
        stroke, fill = ("#F7630C", "#FFF4CE") if focus else ("#0078D4", "#CFE4FA")
        elements.append({
            "id": id_, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
            "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
            "strokeWidth": 2, "roughness": 0, "roundness": {"type": 3},
            "angle": 0, "seed": len(elements) + 1, "version": 1, "versionNonce": 1,
            "isDeleted": False, "groupIds": [], "boundElements": None,
        })
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        size = 15 if w == 345 else 17
        max_chars = int((w - 32) / (size * 0.63))
        wrapped = [
            line for value in lines
            for line in textwrap.wrap(value, width=max_chars, break_long_words=False)
        ]
        label(id_ + "-text", x + 16, y + 14, wrapped, size)
    for i, points in enumerate(edges):
        x, y = points[0]
        elements.append({
            "id": f"edge-{i}", "type": "arrow", "x": x, "y": y,
            "width": max(p[0] for p in points) - min(p[0] for p in points),
            "height": max(p[1] for p in points) - min(p[1] for p in points),
            "points": [[px - x, py - y] for px, py in points],
            "strokeColor": "#0078D4", "backgroundColor": "transparent",
            "strokeWidth": 2, "roughness": 0, "angle": 0, "seed": len(elements) + 1,
            "version": 1, "versionNonce": 1, "isDeleted": False, "groupIds": [],
            "boundElements": None, "startArrowhead": None, "endArrowhead": "arrow",
        })
        coordinates = " ".join(f"{px},{py}" for px, py in points)
        end_x, end_y = points[-1]
        prev_x, prev_y = points[-2]
        if end_x == prev_x:
            dy = -9 if end_y > prev_y else 9
            head = f"{end_x-5},{end_y+dy} {end_x},{end_y} {end_x+5},{end_y+dy}"
        else:
            dx = -9 if end_x > prev_x else 9
            head = f"{end_x+dx},{end_y-5} {end_x},{end_y} {end_x+dx},{end_y+5}"
        svg.append(
            f'<polyline points="{coordinates}" fill="none" stroke="#0078D4" stroke-width="2"/>'
            f'<polyline points="{head}" fill="none" stroke="#0078D4" stroke-width="2"/>'
        )
    for i, (x, y, lines) in enumerate(notes):
        label(f"note-{i}", x, y, lines, 16)
    svg.append("</svg>\n")
    return "\n".join(svg), {
        "type": "excalidraw", "version": 2, "source": "github-copilot",
        "elements": elements, "appState": {"viewBackgroundColor": "#ffffff"}, "files": {},
    }


def build_flow(key):
    title, cards, focus = FLOWS[key]
    nodes = [
        (f"card-{i}", 30 + i * 385, 110, 345, 135, lines, i == focus)
        for i, lines in enumerate(cards)
    ]
    edges = [[(375 + i * 385, 175), (415 + i * 385, 175)] for i in range(3)]
    return _map(
        title, "SECTION MAP | Orange: current focus. Blue: context. Read left to right.",
        nodes, edges,
        [(30, 285, ["Learning sequence, not a live status report. Use the section's read-back and evidence checks."])],
        350,
    )


def build_overview():
    nodes = [
        ("policy", 30, 150, 420, 150, [
            "PART 1 | Purchasing policy PDF", "Direct file upload into Search",
            "Search chunks, embeds and indexes it",
        ], False),
        ("indexes", 30, 330, 420, 150, [
            "PART 1 | Existing Search indexes", "Supplier evidence + approved commitments",
            "Searchable chunks, vectors and metadata",
        ], False),
        ("fabric", 30, 510, 420, 150, [
            "PARTS 2 / 4 | Microsoft Fabric IQ", "OneLake data and ontology relationships",
            "Queried live with user authorization",
        ], False),
        ("workiq", 30, 690, 420, 150, [
            "PARTS 3 / 4 | Work IQ / Microsoft 365", "Workplace actions and discussion",
            "Queried live with user authorization",
        ], False),
        ("model", 530, 130, 470, 135, [
            "PRECONFIGURED | Azure OpenAI", "gpt-5.4: planning / answer synthesis",
            "text-embedding-3-large: text to vectors",
        ], False),
        ("search", 530, 335, 470, 240, [
            "AZURE AI SEARCH | Foundry IQ retrieval",
            "Indexes: vector + text search, semantic rank",
            "Knowledge sources: connections to evidence",
            "Knowledge bases: retrieval orchestration",
            "Six KB variants created across five parts",
        ], True),
        ("local", 1090, 335, 440, 240, [
            "LOCAL | Jupyter / Agent Framework",
            "Parts 1-4: call Search, display KB answer",
            "Part 5: call extractive KB through MCP",
            "Local agent + OpenAI synthesize the answer",
            "No hosted Foundry agent is deployed",
        ], False),
        ("identity", 530, 705, 470, 130, [
            "PRECONFIGURED | Microsoft Entra ID",
            "User sign-in, app scope and federation",
            "Service access != remote source permission",
        ], False),
    ]
    edges = [
        [(450, 225), (490, 225), (490, 455), (530, 455)],
        [(450, 405), (490, 405), (490, 455), (530, 455)],
        [(450, 585), (490, 585), (490, 455), (530, 455)],
        [(450, 765), (490, 765), (490, 455), (530, 455)],
        [(760, 335), (760, 265)],
        [(1000, 455), (1090, 455)],
        [(1310, 335), (1310, 195), (1000, 195)],
        [(760, 705), (760, 575)],
    ]
    notes = [
        (550, 285, ["Parts 1-4: KB calls the model"]),
        (1100, 235, ["Part 5: agent calls the model"]),
        (1090, 610, [
            "Azure Portal: Search objects",
            "Microsoft Foundry: model deployments",
            "Fabric portal: lakehouse and ontology",
            "Entra portal: identity prerequisites",
        ]),
        (30, 890, [
            "Solid arrows show the logical evidence/model boundary, not packet order or a successful live query.",
            "Parts 2 and 3 branch from Part 1. Part 4 combines them. Part 5 intentionally returns to the Part 1 sources.",
            "Services and seed data exist before the lab. Notebooks mainly create Search objects, not new Azure services.",
        ]),
    ]
    return _map(
        "The bigger picture: from enterprise evidence to a grounded answer",
        "SERVICE MAP | Read sources > retrieval > consumer. Orange highlights the main objects you build.",
        nodes, edges, notes, 1100,
    )


def build(stage: str) -> tuple[str, dict]:
    title, kb_name, attached, new = STAGES[stage]
    elements = []
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="1100" viewBox="0 0 1560 1100" role="img" aria-labelledby="title desc">',
        f"<title id='title'>{escape(title)}</title>",
        "<desc id='desc'>Expected architecture, not live deployment status. "
        "Five evidence sources on the left connect to the focused Search knowledge base in the center. "
        "Azure OpenAI is above it. The notebook or local agent is on the right. "
        "Orange marks the new focus, blue reused connections, gray sources not connected to this KB.</desc>",
        '<rect width="1560" height="1100" fill="#ffffff"/>',
    ]

    def box(id_, x, y, w, h, stroke="#8a8886", fill="transparent", dashed=False):
        elements.append({
            "id": id_, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
            "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
            "strokeWidth": 2, "strokeStyle": "dashed" if dashed else "solid",
            "roughness": 0, "roundness": {"type": 3}, "angle": 0,
            "seed": len(elements) + 1, "version": 1, "versionNonce": 1,
            "isDeleted": False, "groupIds": [], "boundElements": None,
        })
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
            f'fill="{fill if fill != "transparent" else "none"}" stroke="{stroke}" stroke-width="2"'
            + (' stroke-dasharray="7 6"' if dashed else "") + "/>"
        )

    def text(id_, x, y, lines, size=18):
        value = "\n".join(lines)
        width = max(len(line) for line in lines) * size * 0.63
        elements.append({
            "id": id_, "type": "text", "x": x, "y": y, "width": width,
            "height": size * 1.5 * len(lines), "text": value, "originalText": value,
            "fontSize": size, "fontFamily": 2, "strokeColor": "#000000",
            "backgroundColor": "transparent", "textAlign": "left", "verticalAlign": "top",
            "angle": 0, "roughness": 0, "seed": len(elements) + 1,
            "version": 1, "versionNonce": 1, "isDeleted": False, "groupIds": [],
            "boundElements": None, "containerId": None, "lineHeight": 1.5,
        })
        spans = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.5}">{escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        svg.append(
            f'<text x="{x}" y="{y + size}" fill="#000000" font-size="{size}" '
            f'font-family="Segoe UI,Arial,sans-serif">{spans}</text>'
        )

    def arrow(id_, points, color="#0078D4"):
        x, y = points[0]
        relative = [[px - x, py - y] for px, py in points]
        elements.append({
            "id": id_, "type": "arrow", "x": x, "y": y,
            "width": max(p[0] for p in points) - min(p[0] for p in points),
            "height": max(p[1] for p in points) - min(p[1] for p in points),
            "points": relative, "strokeColor": color, "backgroundColor": "transparent",
            "strokeWidth": 2, "roughness": 0, "angle": 0, "seed": len(elements) + 1,
            "version": 1, "versionNonce": 1, "isDeleted": False, "groupIds": [],
            "boundElements": None, "startArrowhead": None, "endArrowhead": "arrow",
        })
        svg.append(
            f'<polyline points="{" ".join(f"{px},{py}" for px, py in points)}" '
            f'fill="none" stroke="{color}" stroke-width="2"/>'
        )
        end_x, end_y = points[-1]
        prev_x, prev_y = points[-2]
        if end_x == prev_x:
            dy = -9 if end_y > prev_y else 9
            head = f"{end_x-5},{end_y+dy} {end_x},{end_y} {end_x+5},{end_y+dy}"
        else:
            dx = -9 if end_x > prev_x else 9
            head = f"{end_x+dx},{end_y-5} {end_x},{end_y} {end_x+dx},{end_y+5}"
        svg.append(f'<polyline points="{head}" fill="none" stroke="{color}" stroke-width="2"/>')

    text("title", 30, 15, [title], 28)
    text("subtitle", 30, 62, ["TARGET ARCHITECTURE | Use live read-back and query evidence to verify it"], 17)
    box("cloud", 25, 110, 1110, 825, "#0078D4")
    text("cloud-label", 45, 122, ["CLOUD SERVICES | Azure, Fabric and Microsoft 365"], 18)
    box("local", 1160, 110, 375, 825, "#5C2D91")
    text("local-label", 1180, 122, ["LOCAL | Participant notebook"], 18)

    for i, (key, role, resource, foundation) in enumerate(SOURCES):
        y = 170 + i * 145
        connected = key in attached
        color = "#F7630C" if key in new else "#0078D4" if connected else "#8a8886"
        fill = "#FFF4CE" if key in new else "#CFE4FA" if connected else "#F3F2F1"
        state = "FOCUS THIS PART" if key in new else "REUSED CONNECTION" if connected else "NOT CONNECTED TO THIS KB"
        if stage == "start":
            state = "CREATE IN PART 1" if key == "policy" else "PRECONFIGURED FOUNDATION"
        box(key, 50, y, 535, 125, color, fill, not connected)
        text(key + "-label", 68, y + 7, [role, resource], 18)
        text(key + "-state", 68, y + 66, [state, foundation], 15)
        if connected:
            arrow(key + "-route", [(585, y + 60), (635, y + 60), (635, 560), (680, 560)], color)

    box("model", 680, 185, 425, 155, "#0078D4", "#CFE4FA")
    text("model-label", 700, 200, [
        "PRECONFIGURED | Azure OpenAI",
        "gpt-5.4: reasoning and answer synthesis",
        "text-embedding-3-large: embeddings",
    ], 17)
    box("kb", 680, 455, 425, 200, "#F7630C", "#FFF4CE", stage == "start")
    short_name = kb_name.removesuffix("-knowledge-base")
    text("kb-label", 700, 469, [
        "FOCUSED SEARCH KNOWLEDGE BASE",
        short_name if stage == "start" else short_name + "-",
        "" if stage == "start" else "knowledge-base",
        "No KB connections yet" if stage == "start" else
        "Extractive data | No attached model" if stage == "agent" else
        "Answer synthesis | Model attached",
    ], 16)
    text("source-direction", 690, 678, ["Source arrows: evidence flows into KB.", "Live sources require user authorization."], 16)

    box("consumer", 1180, 455, 335, 200, "#5C2D91", "#E8DAEF")
    text("consumer-label", 1196, 470, [
        "LOCAL AGENT FRAMEWORK" if stage == "agent" else "NOTEBOOK RETRIEVAL CLIENT",
        "MCP: knowledge_base_retrieve" if stage == "agent" else "Call the Search retrieve API",
        "Agent produces final answer" if stage == "agent" else "Display the KB answer",
        "Not a hosted Foundry agent" if stage == "agent" else "Inspect activity and references",
    ], 16)
    if stage not in {"start", "agent"}:
        arrow("kb-model", [(885, 455), (885, 340)])
    if stage != "start":
        arrow("kb-consumer", [(1105, 560), (1180, 560)])
    if stage == "agent":
        arrow("agent-model", [(1495, 455), (1495, 265), (1105, 265)], "#5C2D91")
        text("agent-model-note", 1180, 350, ["Agent calls Azure OpenAI directly.", "KB returns evidence, not an answer."], 16)
    else:
        text("identity-note", 1180, 735, [
            "Parts 2 and 4: Fabric user token",
            "Parts 3 and 4: Work IQ assertion",
            "Service auth is separate from",
            "permission to query live sources.",
        ], 16)
    box("legend", 25, 955, 1510, 120, "#8a8886")
    text("legend-text", 45, 965, [
        "ORANGE: focus/new wiring    BLUE: reused connection    GRAY/DASHED: not connected to the focused KB",
        "Separate KB variants: Part 1 -> Part 2 (Fabric) or Part 3 (Work IQ) -> Part 4 (both). Part 5 reuses Part 1 sources.",
        "Preconfigured data does not mean a knowledge source is connected. Configuration does not prove successful retrieval.",
    ], 17)
    svg.append("</svg>\n")
    scene = {
        "type": "excalidraw", "version": 2, "source": "github-copilot",
        "elements": elements, "appState": {"viewBackgroundColor": "#ffffff"}, "files": {},
    }
    return "\n".join(svg), scene


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    maps = {stage: build(stage) for stage in STAGES}
    maps["overview"] = build_overview()
    maps.update({f"step-{key}": build_flow(key) for key in FLOWS})
    for name, (svg, scene) in maps.items():
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        (OUT / f"{name}.excalidraw").write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(maps)} architecture guides and their editable sources.")


if __name__ == "__main__":
    main()
