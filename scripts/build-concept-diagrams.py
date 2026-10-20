"""Render original teaching diagrams as SVG, PNG and editable Excalidraw scenes."""

import json
import textwrap
from html import escape
from pathlib import Path

import resvg_py


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "concepts"
COLORS = {
    "blue": ("#0078D4", "#EAF4FC"),
    "purple": ("#7052A3", "#F1ECF8"),
    "teal": ("#00838A", "#E5F5F4"),
    "amber": ("#A96C00", "#FFF4D9"),
    "green": ("#107C41", "#E7F4EC"),
    "pink": ("#A32988", "#F9EAF5"),
    "gray": ("#657687", "#F1F4F7"),
}


class Diagram:
    def __init__(self, title, subtitle, height=800):
        self.title, self.subtitle, self.height = title, subtitle, height
        self.elements = []
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="{height}" '
            f'viewBox="0 0 1440 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(subtitle)}</desc>',
            f'<rect width="1440" height="{height}" fill="white"/>',
        ]
        self.text(40, 24, title, 30, bold=True)
        self.text(40, 82, subtitle, 19)
        self.text(40, height - 50, "CONCEPT ILLUSTRATION | Not a portal view, deployed state or saved query result.", 17)

    def element(self, kind, x, y, w, h, **values):
        item = {
            "id": f"e{len(self.elements)}", "type": kind, "x": x, "y": y,
            "width": w, "height": h, "angle": 0, "strokeColor": "#000000",
            "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": 2, "roughness": 0, "opacity": 100,
            "seed": len(self.elements) + 1, "version": 1, "versionNonce": 1,
            "isDeleted": False, "groupIds": [], "boundElements": None,
            **values,
        }
        self.elements.append(item)
        return item

    def text(self, x, y, value, size=20, width=1320, bold=False):
        width = min(width, 1400 - x)
        lines = []
        for line in value.split("\n"):
            lines.extend(textwrap.wrap(
                line, max(1, int(width / (size * 0.60))),
                break_long_words=False, break_on_hyphens=False,
            ) or [""])
        value = "\n".join(lines)
        self.element(
            "text", x, y, width, size * 2.5 * len(lines),
            text=value, originalText=value, fontSize=size, fontFamily=2,
            textAlign="left", verticalAlign="top", lineHeight=1.45, containerId=None,
        )
        spans = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.45}">{escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        self.svg.append(
            f'<text x="{x}" y="{y + size}" fill="#000000" font-size="{size}" '
            f'font-family="Segoe UI,Arial,sans-serif" font-weight="{600 if bold else 400}">{spans}</text>'
        )
        return self.elements[-1]

    def box(self, x, y, w, h, color="blue", container=False, ellipse=False):
        stroke, fill = COLORS[color]
        self.element(
            "ellipse" if ellipse else "rectangle", x, y, w, h,
            strokeColor=stroke, backgroundColor="transparent" if container else fill,
            roundness=None if ellipse else {"type": 3},
        )
        if ellipse:
            self.svg.append(
                f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            )
        else:
            self.svg.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
                f'fill="{"none" if container else fill}" stroke="{stroke}" stroke-width="2"/>'
            )

    def card(self, x, y, w, h, title, body, color="blue"):
        self.box(x, y, w, h, color)
        heading = self.text(x + 20, y + 16, title, 22, w - 40, True)
        offset = max(74, 35 + len(heading["text"].splitlines()) * 22 * 1.45)
        content = self.text(x + 20, y + offset, body, 19, w - 40)
        content_bottom = content["y"] + 19 * 1.45 * len(content["text"].splitlines())
        if content_bottom > y + h - 12:
            raise ValueError(f"Text overflows card: {title}")

    def arrow(self, points, color="blue"):
        stroke = COLORS[color][0]
        x = min(p[0] for p in points)
        y = min(p[1] for p in points)
        self.element(
            "arrow", x, y,
            max(p[0] for p in points) - min(p[0] for p in points),
            max(p[1] for p in points) - min(p[1] for p in points),
            points=[[px - x, py - y] for px, py in points],
            strokeColor=stroke, startArrowhead=None, endArrowhead="arrow",
        )
        coords = " ".join(f"{px},{py}" for px, py in points)
        end_x, end_y = points[-1]
        prev_x, prev_y = points[-2]
        if end_x == prev_x:
            dy = -10 if end_y > prev_y else 10
            head = [(end_x - 6, end_y + dy), (end_x, end_y), (end_x + 6, end_y + dy)]
        else:
            dx = -10 if end_x > prev_x else 10
            head = [(end_x + dx, end_y - 6), (end_x, end_y), (end_x + dx, end_y + 6)]
        self.svg.append(f'<polyline points="{coords}" fill="none" stroke="{stroke}" stroke-width="3"/>')
        self.svg.append(
            f'<polyline points="{" ".join(f"{px},{py}" for px, py in head)}" '
            f'fill="none" stroke="{stroke}" stroke-width="3"/>'
        )

    def result(self):
        return "\n".join(self.svg + ["</svg>\n"]), {
            "type": "excalidraw", "version": 2, "source": "github-copilot",
            "elements": self.elements, "appState": {"viewBackgroundColor": "#ffffff"},
            "files": {},
        }


def build_all():
    diagrams = {}
    d = Diagram("Five evidence roles, five different questions",
                "A useful briefing keeps the authority of each source visible.", 750)
    roles = [
        ("Policy", "What rule applies?", "Purchasing controls\nEscalation responsibilities", "purple"),
        ("Supplier evidence", "What happened?", "Invoices and quality records\nShipment observations", "teal"),
        ("Commitments", "What was approved?", "Agreements and amendments\nPurchase orders", "amber"),
        ("Relationships", "What connects to what?", "Manufacturer and substance\nSubstance and product", "green"),
        ("Workplace", "What is being discussed?", "Current actions and owners\nOpen decisions", "pink"),
    ]
    for i, (title, question, body, color) in enumerate(roles):
        x = 40 + i * 276
        d.card(x, 165, 256, 285, title, question + "\n\n" + body, color)
        d.arrow([(x + 128, 450), (x + 128, 515)], color)
    d.box(40, 520, 1360, 135, container=True)
    d.text(65, 540, "One briefing, with evidence labels and citations", 25, bold=True)
    d.text(65, 591, "A message does not amend a contract. A document mention does not establish an ontology relationship.", 20)
    diagrams["evidence-roles"] = d

    d = Diagram("Why retrieve before asking a model to answer?",
                "Retrieval supplies your organization's evidence. It does not make every answer correct.")
    d.card(40, 165, 400, 210, "Without retrieval", "Question > model knowledge\nNo access to your lab records", "gray")
    d.card(40, 455, 400, 195, "Hard to verify", "Fluent wording is not evidence.\nAsk what supports each claim.", "gray")
    d.arrow([(240, 375), (240, 455)], "gray")
    d.card(520, 165, 880, 155, "With retrieval", "Question > retrieve relevant source material", "blue")
    d.arrow([(960, 320), (960, 380)])
    d.card(520, 380, 880, 155, "Model reads the evidence", "Answer + references + retrieval activity", "green")
    d.text(540, 580, "Agentic retrieval can add model-based query planning and source selection.\nInspect errors and citations even when the answer sounds convincing.", 21, 840)
    diagrams["retrieval-grounding"] = d

    d = Diagram("Two models with different jobs",
                "The embedding model represents meaning. The chat model reads and writes language.")
    d.card(40, 165, 630, 220, "Chat model", "gpt-5.4 in this lab\nInput: question and context\nOutput: a plan or a written answer", "blue")
    d.card(730, 165, 670, 220, "Embedding model", "text-embedding-3-large in this lab\nInput: text\nOutput: a numeric vector, not an answer", "purple")
    d.box(750, 415, 610, 200, "purple", ellipse=True)
    d.text(850, 448, "Nearby meaning\n\"temperature excursion\"\n\"cold-chain temperature alarm\"", 20, 450)
    d.text(65, 440, "Parts 1-4: the KB calls its chat model.\nPart 5: the local agent calls its chat model.\nAn embedding is used for finding evidence.", 22, 580)
    d.text(65, 655, "A deployment name identifies a callable model deployment. It is not the same as the model's job.", 20)
    diagrams["model-roles"] = d

    d = Diagram("From a policy file to searchable passages",
                "Ingestion prepares evidence. Retrieval later selects relevant passages for a question.", 740)
    cards = [
        ("1  Read", "Extract text from\nthe uploaded file.", "purple"),
        ("2  Split", "Keep smaller passages\nwith source metadata.", "teal"),
        ("3  Embed", "Represent each passage\nas a numeric vector.", "purple"),
        ("4  Store", "Index text, vectors\nand citation metadata.", "blue"),
    ]
    for i, (title, body, color) in enumerate(cards):
        x = 40 + i * 350
        d.card(x, 185, 310, 230, title, body, color)
        if i < 3:
            d.arrow([(x + 310, 290), (x + 350, 290)])
    d.card(40, 470, 650, 155, "File source in Part 1", "Upload the policy. The service manages ingestion.", "purple")
    d.card(750, 470, 650, 155, "Existing index sources", "Connect prepared indexes. Do not re-upload their PDFs.", "teal")
    diagrams["document-ingestion"] = d

    d = Diagram("A searchable passage is more than its text",
                "Illustrative index record. Actual fields and reference contents depend on the source.", 880)
    d.box(40, 165, 690, 560, "teal", container=True)
    rows = [
        ("Text passage", "Evidence to read and quote"),
        ("Vector", "Numeric representation for meaning-based search"),
        ("Title, path, page", "Metadata used to trace evidence to a document"),
        ("Chunk and parent IDs", "Identifiers linking passage and source"),
    ]
    for i, (title, body) in enumerate(rows):
        y = 185 + i * 130
        d.box(60, y, 650, 115, "teal")
        d.text(80, y + 10, title, 22, 600, True)
        d.text(80, y + 58, body, 19, 600)
    d.card(850, 185, 550, 155, "Keyword retrieval", "Find literal terms and exact identifiers.", "blue")
    d.card(850, 380, 550, 155, "Vector retrieval", "Find passages with related meaning.", "purple")
    d.arrow([(730, 250), (790, 250), (790, 265), (850, 265)])
    d.arrow([(730, 380), (790, 380), (790, 455), (850, 455)], "purple")
    d.text(855, 585, "Hybrid retrieval combines keyword and vector signals.\nSemantic ranking helps order candidate results.\nNeither creates missing source evidence.", 21, 530)
    diagrams["index-anatomy"] = d

    d = Diagram("A knowledge source is not a knowledge base",
                "A source defines how to reach evidence. A KB coordinates the source connections.", 840)
    d.card(40, 165, 390, 240, "Evidence location", "Uploaded policy\nExisting Search index\nRemote Fabric or Work IQ", "gray")
    d.card(525, 165, 390, 240, "Knowledge source", "Name and useful description\nSource kind\nConnection configuration", "teal")
    d.card(1010, 165, 390, 240, "Knowledge base", "References to sources\nRetrieval settings\nOptional model and output", "blue")
    d.arrow([(430, 285), (525, 285)])
    d.arrow([(915, 285), (1010, 285)])
    d.card(40, 475, 1360, 195, "Reuse connections, compare different KBs",
           "Part 2: three document sources + Fabric. Part 3: three document sources + Work IQ.\nPart 4: all five. Part 5: three document sources, with extractive output.", "blue")
    d.text(65, 704, "Sources do not universally hold the data. Remote source definitions are connections, not bulk copies.", 20)
    diagrams["source-versus-kb"] = d

    d = Diagram("Follow a citation instead of trusting the wording",
                "Illustrative identifiers only. Inspect the actual response, references and activity in your run.", 850)
    d.card(40, 175, 340, 210, "1  Answer marker", "A claim ends in [ref:3].\nFind reference id 3.", "blue")
    d.card(490, 175, 420, 260, "2  Reference", "id: 3\nactivitySource: 2\nSource metadata and evidence", "teal")
    d.card(1020, 175, 380, 260, "3  Activity", "id: 2\nSource call and sub-query\nTiming, warnings or errors", "purple")
    d.arrow([(380, 280), (490, 280)])
    d.arrow([(910, 280), (1020, 280)], "purple")
    d.card(490, 530, 910, 155, "4  Check the underlying source",
           "For an indexed reference, inspect title, path and page metadata when returned.", "teal")
    d.arrow([(700, 435), (700, 530)], "teal")
    d.text(45, 490, "Configured\nis not the same as\ncalled or cited.", 23, 370)
    d.text(65, 728, "Fabric and Work IQ references have different shapes. A citation still needs evidence that supports the claim.", 20)
    diagrams["citation-trail"] = d

    d = Diagram("Three authorization contexts, not one universal key",
                "Search access and permission to remote evidence are separate checks.", 950)
    lanes = [
        ("Search service", "Lab admin key", "Create Search objects and access document retrieval.\nAlso authenticates the Part 5 MCP connection.", "blue"),
        ("Fabric", "Delegated user token", "query_source_authorization\nRemote access is evaluated for the signed-in user.", "green"),
        ("Work IQ", "Work IQ user assertion", "query_work_iq_source_authorization\nApp/federation trust supports the on-behalf-of flow.", "pink"),
    ]
    for i, (title, credential, body, color) in enumerate(lanes):
        y = 170 + i * 215
        d.card(40, y, 380, 175, title, credential, color)
        d.arrow([(420, y + 85), (510, y + 85)], color)
        d.box(510, y, 890, 175, color)
        d.text(535, y + 20, body, 22, 840)
    d.text(65, 815, "Never print keys, tokens or assertions. An admin key does not grant Fabric workspace or Microsoft 365 permissions.", 20)
    diagrams["authorization-lanes"] = d

    d = Diagram("Read an ontology as explicit business relationships",
                "Schematic entity types, not a claim about any particular supplier or product.", 760)
    d.card(40, 190, 390, 180, "Manufacturer", "A business entity", "green")
    d.card(525, 190, 390, 180, "Active substance", "A business entity", "green")
    d.card(1010, 190, 390, 180, "Medicinal product", "A business entity", "green")
    d.arrow([(430, 280), (525, 280)], "green")
    d.arrow([(1010, 280), (915, 280)], "green")
    d.text(430, 140, "manufactures", 18, 180)
    d.text(935, 140, "contains", 18, 180)
    d.card(40, 445, 650, 185, "Document evidence", "Use invoice and quality records for lot-level facts.\nA mention is not an ontology edge.", "teal")
    d.card(750, 445, 650, 185, "Fabric evidence", "Use returned relationships for business dependencies.\nDo not invent an absent relationship.", "green")
    diagrams["ontology-relationships"] = d

    d = Diagram("Workplace updates and approved commitments",
                "Compare the evidence. Do not silently turn a discussion into a contractual change.", 790)
    d.card(40, 175, 540, 340, "Work IQ context", "Current actions and owners\nDeadlines people are discussing\nUnresolved approvals and risks\n\nOnly what the user may access", "pink")
    d.card(860, 175, 540, 340, "Approved sourcing records", "Agreement and amendment terms\nPurchase-order commitments\nApproved quantities and dates\n\nCheck the actual cited record", "amber")
    d.arrow([(580, 440), (860, 440)], "gray")
    d.arrow([(860, 490), (580, 490)], "gray")
    d.text(610, 190, "COMPARE\nOwner\nDeadline\nDecision\nConflict", 21, 230)
    d.box(40, 575, 1360, 110, "gray")
    d.text(65, 597, "If an update conflicts with a commitment, report the conflict and the missing decision.\nDo not claim that the update changed the approved record.", 22)
    diagrams["workplace-versus-commitment"] = d

    d = Diagram("Who writes the final answer?",
                "Reasoning effort and output mode are different settings. These are the two lab patterns.", 930)
    d.card(40, 165, 650, 210, "Parts 1-4: KB synthesis", "Multi-source KBs use low reasoning.\nOutput: answerSynthesis\nThe KB calls its attached chat model.", "blue")
    d.card(750, 165, 650, 210, "Part 5: agent synthesis", "KB uses minimal reasoning.\nOutput: extractiveData\nNo chat model is attached to this KB.", "purple")
    d.card(40, 470, 650, 175, "Answer, references, activity", "Inspect the KB's response and source evidence.", "blue")
    d.card(750, 470, 650, 175, "Evidence over MCP", "The local agent calls its own model to answer.", "purple")
    d.arrow([(365, 375), (365, 470)])
    d.arrow([(1075, 375), (1075, 470)], "purple")
    d.text(65, 705, "Part 5 uses only the three Part 1 source types, not the five-source Part 4 KB.\nMCP is the tool protocol. The agent runs in your notebook, not as a hosted Foundry agent.", 22)
    diagrams["answer-boundary"] = d

    d = Diagram("Azure resource containers and identity",
                "A simplified orientation map. Not every workload is nested inside an Azure resource group.", 980)
    d.box(40, 155, 1360, 650, "gray", container=True)
    d.text(65, 175, "Tenant: organization identity boundary in Microsoft Entra ID", 25)
    d.box(70, 245, 1300, 330, "blue", container=True)
    d.text(95, 265, "Azure subscription: billing and access scope", 23)
    d.box(100, 335, 1240, 210, "blue", container=True)
    d.text(125, 350, "Resource group: lifecycle and management grouping", 22)
    d.box(125, 425, 560, 85, "blue")
    d.text(145, 442, "Azure AI Search service", 23)
    d.box(735, 425, 580, 85, "purple")
    d.text(755, 442, "Model-hosting Azure resources", 23)
    d.box(70, 630, 620, 120, "green")
    d.text(95, 650, "Fabric workspace\nSeparate data and permission boundary", 22, 570)
    d.box(750, 630, 620, 120, "pink")
    d.text(775, 650, "Microsoft 365\nUser-scoped workplace content", 22, 570)
    d.text(65, 850, "A resource endpoint tells you where to call. A credential proves identity or access.\nPermissions still determine what that identity can do.", 22)
    diagrams["azure-scopes"] = d
    return diagrams


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, diagram in build_all().items():
        svg, scene = diagram.result()
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        (OUT / f"{name}.excalidraw").write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
        (OUT / f"{name}.png").write_bytes(resvg_py.svg_to_bytes(svg_string=svg))
    print(f"Rendered {len(build_all())} concept diagrams in SVG, PNG and Excalidraw.")


if __name__ == "__main__":
    main()
