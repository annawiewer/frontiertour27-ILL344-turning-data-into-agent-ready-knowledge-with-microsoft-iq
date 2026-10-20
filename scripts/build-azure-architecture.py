"""Render the lab's service architecture using official icons and local Graphviz."""

import base64
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

import resvg_py


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "architecture"
ICONS = OUT / "icons"
spec = importlib.util.spec_from_file_location("lab_diagrams", ROOT / "scripts" / "build-lab-diagrams.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
STAGES = lab.STAGES
BLUE = "#0078D4"
PURPLE = "#5242B8"
GRAY = "#687787"
ORANGE = "#D76B00"
DESCRIPTIONS = {
    "overview": (
        "A local notebook asks Search to retrieve policy, indexed documents and live Fabric / Work IQ data.",
        "Parts 1-4 use the KB model for answers. In Part 5, a local MCP agent writes the final answer.",
    ),
    "start": (
        "Search, model deployments, indexed documents and remote data already exist in the lab.",
        "The notebook is a local client. The attendee has not created a knowledge base yet.",
    ),
    "policy": (
        "Part 1 uploads the purchasing policy and connects it to a dedicated Search knowledge base.",
        "The KB retrieves policy evidence and calls the existing model to return a cited answer.",
    ),
    "documents": (
        "A separate Search knowledge base connects policy with two preloaded document indexes.",
        "The KB combines the three evidence sources and uses its model to return a cited answer.",
    ),
    "fabric": (
        "This KB adds live Fabric ontology relationships to the three Part 1 evidence sources.",
        "Fabric data stays in its workspace. Queries require delegated user access, not a data copy.",
    ),
    "workiq": (
        "This KB adds permission-scoped Work IQ context to the three Part 1 sources, without Fabric.",
        "Workplace discussions complement document evidence but do not establish contractual approval.",
    ),
    "combined": (
        "This KB connects all five source roles: policy, two document indexes, Fabric and Work IQ.",
        "Search retrieves the evidence and calls its model to produce a cross-source, cited briefing.",
    ),
    "agent": (
        "A local Python agent calls an extractive three-source KB through knowledge_base_retrieve.",
        "The KB has no model. The agent calls Azure OpenAI for the final answer. No hosted agent is created.",
    ),
}
WALKTHROUGHS = {
    "overview": [
        "Start with the participant device. The notebook or Python agent runs locally, not in Azure.",
        "Follow the dashed gray identity arrow to Entra ID. Sign-in supplies the user authorization needed by the client and permission-scoped sources.",
        "In Part 1, follow the dashed gray upload and embedding connections. The policy becomes searchable in a file knowledge source. The two document indexes already exist.",
        "Follow the solid blue arrow from the client to the selected Search KB, then from the KB to its connected evidence sources. Fabric and Work IQ stay remote and are queried live.",
        "For Parts 1-4, follow the solid purple arrow from the KB to Azure OpenAI. The KB uses its attached model for planning and answer synthesis.",
        "For Part 5, follow the separate purple arrow from the local agent to Azure OpenAI. The agent calls an extractive KB over MCP, then writes the final answer itself.",
        "Return to the notebook output. Check citations, source activity and references. Responses travel back over the same connections, so no reverse arrows are drawn.",
    ],
    "start": [
        "Locate the participant device and load the notebook environment variables. This configures a local client, not a new Azure deployment.",
        "Follow the dashed gray arrow to Entra ID and sign in. Keep tokens and environment-specific identifiers out of shared files.",
        "Inspect the preconfigured Azure AI Search service, its two indexes, and the Foundry model deployments.",
        "Locate the separate Fabric workspace and Microsoft 365 boundary. Their data and identity prerequisites are prepared outside the notebook.",
        "Notice the gray KB and source cards. No attendee KB exists at this point, so no blue retrieval or purple KB model-call arrows are shown.",
    ],
    "policy": [
        "Configure the local notebook and sign in through Entra ID. The dashed gray identity arrow represents authentication.",
        "Create the file knowledge source and upload the purchasing policy. Follow the dashed gray connections from the PDF to the file source and from the source to the embedding model.",
        "Wait for ingestion and inspect the uploaded file status. A successful upload alone does not prove that the policy is searchable.",
        "Create the policy KB with the file source and the existing synthesis model. Follow the solid blue notebook-to-KB arrow when you submit a question.",
        "Follow the blue KB-to-file-source arrow for evidence and the purple KB-to-model arrow for planning and answer synthesis.",
        "Read the cited policy answer in the notebook and verify its file reference and source activity. The response returns on the same connections.",
    ],
    "documents": [
        "Reuse the ingested policy and the preloaded supplier-evidence and sourcing-documents indexes. Do not upload those indexed documents again.",
        "Create the two search-index knowledge source definitions, then create a separate KB connecting all three sources.",
        "Submit a question from the local notebook. Follow the solid blue connection to this three-source KB.",
        "Follow the blue connections from the KB to the policy source and the existing indexes. The indexes box represents two distinct document sources.",
        "Follow the purple connection to Azure OpenAI for planning and a grounded, cited answer. The dashed gray embedding connection belongs to policy ingestion, not every query.",
        "Check activity and references to see which sources actually supplied evidence. Configuration alone does not prove that all three were used.",
    ],
    "fabric": [
        "Sign in and acquire the delegated user token. The dashed gray Entra connection supplies authorization for live Fabric access.",
        "Create source definitions for the Part 1 evidence and the existing Fabric ontology, then create a four-source KB. This branches from Part 1 rather than modifying its KB.",
        "Send a question from the notebook to the KB over the solid blue connection.",
        "Follow the blue connections to the policy, the two document indexes, and Fabric IQ. The dashed gray ontology-to-OneLake connection represents access to existing structured data, not a copy into Search.",
        "Follow the purple KB-to-model connection for planning and answer synthesis.",
        "Inspect the returned Fabric activity and references alongside document evidence. An existing ontology does not prove this query used it.",
    ],
    "workiq": [
        "Sign in and acquire the delegated user token. Entra prerequisites and the user assertion enable permission-scoped Work IQ retrieval.",
        "Create the indexed and Work IQ source definitions, then create a four-source KB with the policy. This branch does not include Fabric.",
        "Send the question from the local notebook to the KB over the solid blue connection.",
        "Follow the blue connections to policy, document indexes and Work IQ. Workplace context remains in Microsoft 365 and is retrieved with the user's permissions.",
        "Follow the purple KB-to-model connection for planning and answer synthesis. Workplace discussion is context, not contractual approval.",
        "Inspect Work IQ activity and returned references. Use the notebook SDK/API read-back for Work IQ configuration, not an assumed portal editor.",
    ],
    "combined": [
        "Configure the notebook and acquire delegated authorization through Entra ID before querying live Fabric and Work IQ sources.",
        "Create source definitions and a separate combined KB with five sources: policy, supplier evidence, sourcing documents, Fabric ontology and Work IQ.",
        "Follow the solid blue notebook-to-KB arrow to submit the cross-source question.",
        "Follow the outgoing blue arrows to the evidence sources. The indexes box counts as two sources. Fabric accesses existing OneLake relationships and Work IQ queries existing workplace context.",
        "Follow the purple KB-to-Azure OpenAI arrow for planning and answer synthesis. Remote source data is not bulk-copied into Search.",
        "Read the cited briefing in the notebook. Compare activity and references with each claim rather than assuming every connected source contributed.",
    ],
    "agent": [
        "Configure the local agent environment and authentication for the KB's MCP endpoint. No hosted Foundry agent is deployed.",
        "Create a separate three-source KB using policy and the two document indexes. Set extractiveData, minimal reasoning and no KB-attached model.",
        "Create the MCP tool client and the local Python agent with its Azure OpenAI model client.",
        "Run a question and follow the solid blue agent-to-KB arrow. The agent invokes knowledge_base_retrieve over MCP and the KB retrieves evidence from its three sources.",
        "Follow the purple arrow directly from the local agent to Azure OpenAI. The agent, not the KB, synthesizes the final answer from the returned extracts.",
        "Inspect the answer and tool-call trace in the notebook. Fabric and Work IQ are gray and disconnected from this KB. The dashed gray policy embedding path belongs to earlier ingestion.",
    ],
}


def legend_label():
    rows = (
        (BLUE, "&#9473;&#9473;&#9654;", "Blue, solid: retrieve evidence / call the KB (REST or MCP)"),
        (PURPLE, "&#9473;&#9473;&#9654;", "Purple, solid: model call for planning / answer synthesis"),
        (GRAY, "- - &#9654;", "Gray, dashed: sign-in, upload, embeddings or source data access"),
        (ORANGE, "&#9632;", "Orange boxes: focus of this phase. Gray boxes: not connected to this KB."),
    )
    return (
        '<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">'
        '<TR><TD COLSPAN="2"><FONT POINT-SIZE="13"><B>Arrow and object legend</B></FONT></TD></TR>'
        + "".join(
            f'<TR><TD ALIGN="RIGHT"><FONT COLOR="{color}" POINT-SIZE="18"><B>{sample}</B></FONT></TD>'
            f'<TD ALIGN="LEFT"><FONT POINT-SIZE="12">{escape(text)}</FONT></TD></TR>'
            for color, sample, text in rows
        )
        + '</TABLE>'
    )


def check_icons():
    """Reject changed icons and stale Foundry branding before rendering."""
    manifest = json.loads((ICONS / "sources.json").read_text(encoding="utf-8"))
    for name, source in manifest["icons"].items():
        data = (ICONS / source["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"Official icon changed: {name}")
    if "#302ec9" not in (ICONS / "foundry.svg").read_text(encoding="utf-8").lower():
        raise ValueError("Microsoft Foundry icon must use the current purple branding")
    return manifest


def label(title, lines=(), icon=None):
    image = (
        f'<TR><TD WIDTH="56" HEIGHT="56" FIXEDSIZE="TRUE">'
        f'<IMG SRC="icons/{icon}.png" SCALE="TRUE"/></TD></TR>'
        if icon else ""
    )
    body = "".join(
        f'<TR><TD><FONT POINT-SIZE="12">{escape(line)}</FONT></TD></TR>'
        for line in lines
    )
    return (
        '<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">'
        f'{image}<TR><TD><B>{escape(title)}</B></TD></TR>{body}</TABLE>'
    )


def build(stage):
    overview = stage == "overview"
    if not overview and stage not in STAGES:
        raise ValueError(f"Unknown architecture stage: {stage}")
    if overview:
        title = "Agent-ready knowledge: Azure service architecture"
        kb_name, attached, new = "Six KB variants across five parts", lab.BASE | {"fabric", "workiq"}, set()
    else:
        title, kb_name, attached, new = STAGES[stage]
    foundation = stage == "start"
    agent = stage == "agent"
    client_enabled = not foundation
    notebook_enabled = client_enabled and not agent
    agent_enabled = overview or agent
    lines = [
        'digraph Architecture {',
        'graph [rankdir=LR, bgcolor="white", compound=true, newrank=true,',
        '  pad="0.35", nodesep="0.65", ranksep="1.15", splines=ortho,',
        '  fontname="Segoe UI", fontsize=24, labelloc=t, '
        'label=<<TABLE BORDER="0" CELLBORDER="0" CELLPADDING="5">'
        f'<TR><TD><B>{escape(title)}</B></TD></TR>'
        + "".join(
            f'<TR><TD><FONT POINT-SIZE="14">{escape(sentence)}</FONT></TD></TR>'
            for sentence in DESCRIPTIONS[stage]
        ) +
        '<TR><TD><FONT POINT-SIZE="12">Arrows: caller to dependency. Responses return on the same connection.</FONT></TD></TR>'
        f'<TR><TD>{legend_label()}</TD></TR>'
        '<TR><TD><FONT POINT-SIZE="12">Logical lab architecture, not live status. Public endpoints, no VNet / private endpoints.</FONT></TD></TR>'
        '</TABLE>>];',
        'node [shape=plain, fontname="Segoe UI", fontsize=15, fontcolor="#172B4D"];',
        f'edge [fontname="Segoe UI", fontsize=11, color="{BLUE}", fontcolor="{BLUE}",',
        '  arrowsize=1.0, penwidth=3.2];',
    ]

    def cluster(id_, title_, color, fill, icon=None, details=()):
        heading = f"<{label(title_, details, icon)}>" if icon else json.dumps(title_)
        lines.extend([
            f'subgraph cluster_{id_} {{',
            f'label={heading}; fontsize=17; fontcolor="{color}";',
            f'color="{color}"; fillcolor="{fill}"; style="rounded,filled"; penwidth=1.2; margin=22;',
        ])

    def node(id_, title_, details=(), icon=None, active=True, focus=False):
        border = ORANGE if focus else BLUE if active else "#B9C1CA"
        fill = "#FFF6E8" if focus else "white" if active else "#F5F6F8"
        lines.append(
            f'{id_} [shape=box, style="rounded,filled", color="{border}", '
            f'fillcolor="{fill}", penwidth=1.3, margin="0.13,0.10", '
            f'label=<{label(title_, details, icon)}>];'
        )

    def edge(from_, to_, text, kind="query", constraint=True):
        color = PURPLE if kind == "model" else GRAY if kind in {"identity", "setup"} else BLUE
        style = "dashed" if kind in {"identity", "setup"} else "solid"
        lines.append(
            f'{from_} -> {to_} [tooltip={json.dumps(text)}, color="{color}", '
            f'fontcolor="{color}", style="{style}", constraint={str(constraint).lower()}];'
        )

    cluster("local", "PARTICIPANT DEVICE  |  not hosted in Azure", PURPLE, "#F8F6FC")
    node("notebook", "Jupyter notebook", [
        "Local Python client",
        "Parts 1-4: display the KB answer" if notebook_enabled else "Other parts: reference only",
    ], "browser", notebook_enabled)
    if overview or agent:
        node("agent", "Microsoft Agent Framework", [
            "Part 5: local Python agent", "MCP tool + model client", "Not a hosted Foundry agent",
        ], active=agent_enabled, focus=agent)
    node("pdf", "Purchasing policy PDF", ["Local input, uploaded in Part 1"], active=True)
    lines.append("}")

    cluster("azure", "AZURE RESOURCE GROUP  |  preconfigured services", BLUE, "#F4F9FF")
    cluster("search", "Azure AI Search  |  Foundry IQ retrieval", BLUE, "#FFFFFF", "search", [
        "Vector + full-text search, semantic ranking",
        "System-assigned managed identity",
    ])
    if overview:
        kb_lines = ["Separate KBs, not one growing KB", "Parts 1-4: answerSynthesis", "Part 5: extractiveData / minimal"]
    elif foundation:
        kb_lines = ["No attendee KB created yet", "Create sources and KBs in the lab"]
    else:
        short = kb_name.removesuffix("-knowledge-base")
        kb_lines = [short + "-", "knowledge-base", f"{len(attached)} connected source definitions"]
        kb_lines.append("extractiveData / minimal / no model" if agent else "answerSynthesis / model attached")
    node("kb", "Knowledge base + source definitions", kb_lines, "foundry-iq",
         not foundation, not foundation)
    node("indexes", "Existing Search indexes", [
        "supplier-evidence", "sourcing-documents",
        "Chunks, vectors and citation metadata",
        "Connected" if "evidence" in attached else "Preloaded, not connected to this KB",
    ], active="evidence" in attached, focus=bool(new & {"evidence", "sourcing"}))
    node("policy", "File knowledge source", [
        "Uploaded policy chunks + vectors" if "policy" in attached else "Create and ingest in Part 1",
        "file-docs-knowledge-source",
    ], active="policy" in attached, focus="policy" in new)
    lines.append("}")
    cluster("foundry", "Microsoft Foundry  |  existing account + project", PURPLE, "#F7F6FD")
    node("models", "Azure OpenAI model deployments", [
        "gpt-5.4: planning / answer synthesis",
        "text-embedding-3-large: text to vectors",
    ], "foundry")
    lines.extend(["}", "}"])

    fabric_active = "fabric" in attached
    cluster("fabric", "FABRIC WORKSPACE  |  separate SaaS boundary", "#157B62", "#F1FAF6")
    node("ontology", "Microsoft Fabric IQ", [
        "Existing ontology relationships",
        "Manufacturer > substance > product",
        "Live source" if fabric_active else "Not connected to this KB",
    ], "fabric", fabric_active, "fabric" in new)
    node("lakehouse", "OneLake / lakehouse", ["Existing structured data", "Backed by lab Fabric capacity"], "lakehouse")
    lines.append("}")

    workiq_active = "workiq" in attached
    cluster("m365", "MICROSOFT 365  |  separate SaaS boundary", PURPLE, "#F8F6FC")
    node("workiq", "Work IQ", [
        "Existing workplace context",
        "User-permission-scoped retrieval",
        "Discussion is not contractual approval",
        "Live source" if workiq_active else "Not connected to this KB",
    ], active=workiq_active, focus="workiq" in new)
    lines.append("}")

    cluster("identity", "TENANT-WIDE IDENTITY  |  not a resource inside the lab resource group", GRAY, "#F7F8FA")
    node("entra", "Microsoft Entra ID", [
        "User sign-in and delegated access",
        "App scope + Work IQ federation",
        "Search managed identity: service access",
    ], "entra")
    lines.append("}")

    # Invisible constraints keep resource boundaries in consistent reading order.
    lines.extend([
        'notebook -> kb [style=invis, weight=5];',
        'kb -> ontology [style=invis, weight=5];',
        'kb -> workiq [style=invis, weight=5];',
        '{rank=same; notebook; pdf; entra;' + ("agent;" if overview or agent else "") + "}",
        '{rank=same; kb; indexes; policy; models;}',
        '{rank=same; ontology; lakehouse; workiq;}',
    ])
    if notebook_enabled:
        edge("notebook", "kb", "1  Retrieve API\nQuestion / cited KB answer")
    if agent_enabled:
        edge("agent", "kb", "Part 5  MCP\nknowledge_base_retrieve\nExtracts, not a KB answer")
        edge("agent", "models", "Part 5  Direct model call\nAgent writes the final answer", "model")
    if not foundation and not agent:
        edge("kb", "models", "Parts 1-4  Plan + synthesize" if overview else "Plan + synthesize", "model")
    if "policy" in attached:
        edge("pdf", "policy", "Part 1  Upload + ingest", "setup")
        edge("policy", "models", "Embedding generation", "setup")
        edge("kb", "policy", "Retrieve policy")
    if "evidence" in attached:
        edge("kb", "indexes", "Query existing indexes")
    if fabric_active:
        edge("kb", "ontology", "Live ontology query\nDelegated user authorization")
    if workiq_active:
        edge("kb", "workiq", "Live Work IQ query\nUser assertion")
    edge("ontology", "lakehouse", "Structured relationships / data", "setup")
    edge("notebook", "entra", "User authentication", "identity", False)
    lines.append("}")
    return "\n".join(lines) + "\n"


def route_service_connections(svg):
    """Keep model and identity trunks outside container headings, which dot does not avoid."""
    ns = "{http://www.w3.org/2000/svg}"
    ET.register_namespace("", ns[1:-1])
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring(svg)
    groups = {}
    for group in root.iter(ns + "g"):
        title = group.find(ns + "title")
        if title is not None:
            groups[title.text] = group

    def bounds(name):
        path = groups[name].find(ns + "path")
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.attrib["d"])]
        return min(numbers[::2]), min(numbers[1::2]), max(numbers[::2]), max(numbers[1::2])

    def center(box):
        return (box[1] + box[3]) / 2

    def reroute(name, points, incoming):
        group = groups[name]
        path = group.find(".//" + ns + "path")
        path.set("d", "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points))
        x, y = points[-1]
        back = x - 12 if incoming == "left" else x + 12
        group.find(".//" + ns + "polygon").set(
            "points", f"{x:.2f},{y:.2f} {back:.2f},{y - 5:.2f} {back:.2f},{y + 5:.2f}"
        )

    models = bounds("models")
    search = bounds("cluster_search")
    azure = bounds("cluster_azure")
    local = bounds("cluster_local")
    left_lane = (azure[0] + search[0]) / 2
    right_lane = (azure[2] + search[2]) / 2
    if "kb->models" in groups:
        kb = bounds("kb")
        y = center(models) + 18
        reroute("kb->models", [(kb[0], kb[3] - 24), (left_lane, kb[3] - 24),
                              (left_lane, y), (models[0], y)], "left")
    if "agent->models" in groups:
        agent = bounds("agent")
        lane = (local[2] + azure[0]) / 2
        y = center(models) - 18
        reroute("agent->models", [(agent[2], center(agent)), (lane, center(agent)),
                                 (lane, y), (models[0], y)], "left")
    if "policy->models" in groups:
        policy = bounds("policy")
        y = center(models)
        reroute("policy->models", [(policy[2], center(policy)), (right_lane, center(policy)),
                                  (right_lane, y), (models[2], y)], "right")
    notebook = bounds("notebook")
    entra = bounds("entra")
    lane = min(local[0], entra[0]) - 24
    reroute("notebook->entra", [(notebook[0], center(notebook)), (lane, center(notebook)),
                               (lane, center(entra)), (entra[0], center(entra))], "left")

    # A white casing makes crossings unambiguous without implying a junction.
    for group in groups.values():
        if group.attrib.get("class") != "edge":
            continue
        path = group.find(".//" + ns + "path")
        parent = next(p for p in group.iter() if path in list(p))
        casing = ET.Element(ns + "path", {
            "d": path.attrib["d"], "fill": "none", "stroke": "white", "stroke-width": "7.2",
        })
        parent.insert(list(parent).index(path), casing)
    return ET.tostring(root, encoding="unicode")


def build_part1_reveal(complete=False):
    """Keep later parts covered while revealing the objects built in Part 1."""
    stage = "documents" if complete else "policy"
    ns = "{http://www.w3.org/2000/svg}"
    ET.register_namespace("", ns[1:-1])
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring((OUT / f"azure-{stage}.svg").read_text(encoding="utf-8"))
    graph = root.find(ns + "g")
    groups = {
        group.find(ns + "title").text: group
        for group in graph.findall(ns + "g")
        if group.find(ns + "title") is not None
    }
    title = "Part 1 complete: three connected evidence sources" if complete else "Part 1 begins: build the policy path"
    descriptions = (
        (
            "Built: a policy file source, two index source definitions and a three-source knowledge base.",
            "Orange shows your completed Part 1 configuration. Fabric and Work IQ remain covered.",
        )
        if complete else (
            "First build: upload one policy and create its file source and policy-only knowledge base.",
            "Orange is your current build target. Faded indexes come next. Covered areas belong to later parts.",
        )
    )
    replacements = dict(zip(DESCRIPTIONS[stage], descriptions))
    replacements[STAGES[stage][0]] = title
    for text in graph.findall(ns + "text"):
        if text.text in replacements:
            text.text = replacements[text.text]
            # Center the new captions rather than reusing the old text's start position.
            text.set("text-anchor", "middle")
            text.set("x", str(float(root.attrib["viewBox"].split()[2]) / 2 - 25.2))

    for name in ("cluster_identity", "entra", "notebook->entra"):
        groups[name].set("opacity", "0.18")
    for name in ("cluster_foundry", "models"):
        groups[name].set("opacity", "0.55")
    for name in ("cluster_azure", "cluster_local"):
        groups[name].set("opacity", "0.55")
    if not complete:
        groups["indexes"].set("opacity", "0.12")
    for name in ("kb", "policy", "indexes") if complete else ("kb", "policy"):
        shape = groups[name].find(ns + "path")
        shape.set("fill", "#FFF0D8")
        shape.set("stroke", ORANGE)
        shape.set("stroke-width", "3")

    for cluster, caption in (
        ("cluster_fabric", "Later: Fabric IQ (Parts 2 / 4)"),
        ("cluster_m365", "Later: Work IQ (Parts 3 / 4)"),
    ):
        shape = groups[cluster].find(ns + "path")
        coordinates = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", shape.attrib["d"])]
        left, right = min(coordinates[::2]), max(coordinates[::2])
        top, bottom = min(coordinates[1::2]), max(coordinates[1::2])
        cover = ET.SubElement(graph, ns + "g", {"data-part1-cover": cluster})
        ET.SubElement(cover, ns + "rect", {
            "x": str(left), "y": str(top), "width": str(right - left),
            "height": str(bottom - top), "rx": "12",
            "fill": "#F4F5F7", "fill-opacity": "0.98", "stroke": "#D8DDE3",
        })
        text = ET.SubElement(cover, ns + "text", {
            "x": str((left + right) / 2), "y": str((top + bottom) / 2),
            "text-anchor": "middle", "font-family": "Segoe UI",
            "font-size": "15", "fill": "#687787",
        })
        text.text = caption
    root.set("aria-label", title + ". " + " ".join(descriptions) + " Target architecture, not a live deployment status.")
    return ET.tostring(root, encoding="unicode")


def render_part1_reveals():
    for complete, name in ((False, "part1-before"), (True, "part1-after")):
        svg = build_part1_reveal(complete)
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        (OUT / f"{name}.png").write_bytes(resvg_py.svg_to_bytes(svg_string=svg, width=1800, dpi=96))
        print(f"Rendered {name}: staged Part 1 SVG and PNG")


PART_REVEALS = {
    2: {
        "stage": "fabric", "focus": ("kb", "ontology"),
        "new_edges": ("notebook->kb", "kb->ontology", "kb->policy", "kb->indexes", "kb->models"),
        "covers": {"cluster_m365": "Separate branch: Work IQ (Parts 3 / 4)"},
        "before": (
            "Part 2 begins: connect Fabric relationships",
            "Reuse the three Part 1 sources. Create a separate four-source KB with a Fabric ontology connection.",
            "Orange dashed cards are the build target. Faded documents and services already exist. Work IQ stays covered.",
        ),
        "after": (
            "Part 2 complete: documents plus Fabric relationships",
            "Built: a Fabric source connection and a separate four-source KB. The Part 1 KB remains unchanged.",
            "Orange highlights the completed configuration. Fabric data stays remote. Verify actual query evidence.",
        ),
    },
    3: {
        "stage": "workiq", "focus": ("kb", "workiq"),
        "new_edges": ("notebook->kb", "kb->workiq", "kb->policy", "kb->indexes", "kb->models"),
        "covers": {"cluster_fabric": "Separate branch: Fabric IQ (Parts 2 / 4)"},
        "before": (
            "Part 3 begins: connect workplace context",
            "Return to the three Part 1 sources. Create a separate four-source KB with Work IQ, without Fabric.",
            "Orange dashed cards are the build target. Faded documents and services already exist. Fabric stays covered.",
        ),
        "after": (
            "Part 3 complete: documents plus Work IQ context",
            "Built: a Work IQ connection and a separate four-source KB. This is a sibling of the Fabric KB.",
            "Orange highlights the completed configuration. User permissions still govern workplace retrieval.",
        ),
    },
    4: {
        "stage": "combined", "focus": ("kb",),
        "new_edges": ("notebook->kb", "kb->ontology", "kb->workiq", "kb->policy", "kb->indexes", "kb->models"),
        "covers": {},
        "before": (
            "Part 4 begins: combine the five source roles",
            "Reuse the document, Fabric and Work IQ source definitions. Create a separate combined KB.",
            "The orange dashed KB is the build target. Faded sources already exist. Faint arrows show planned wiring.",
        ),
        "after": (
            "Part 4 complete: one five-source configuration",
            "Built: a separate KB connecting policy, two document indexes, Fabric and Work IQ.",
            "Orange highlights the new combined KB. Visible connections are configuration, not proof all sources answered.",
        ),
    },
    5: {
        "stage": "agent", "focus": ("kb", "agent"),
        "new_edges": ("agent->kb", "agent->models", "kb->policy", "kb->indexes"),
        "covers": {
            "cluster_fabric": "Not used by this KB: Fabric IQ",
            "cluster_m365": "Not used by this KB: Work IQ",
        },
        "before": (
            "Part 5 begins: build an extractive KB and local agent",
            "Reuse only the three Part 1 sources. Build a new model-free KB and a local MCP agent.",
            "Orange dashed cards are the build target. Faded services already exist. Fabric and Work IQ stay covered.",
        ),
        "after": (
            "Part 5 complete: local agent over an extractive KB",
            "Built: a three-source extractive KB and a local MCP agent. The agent calls the model, not the KB.",
            "Orange highlights the completed build. No hosted agent, Fabric connection or Work IQ connection is created.",
        ),
    },
}


def build_part_reveal(part, complete=False):
    """Stage each independent KB branch without implying a live deployment check."""
    config = PART_REVEALS[part]
    stage = config["stage"]
    title, *descriptions = config["after" if complete else "before"]
    ns = "{http://www.w3.org/2000/svg}"
    ET.register_namespace("", ns[1:-1])
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring((OUT / f"azure-{stage}.svg").read_text(encoding="utf-8"))
    graph = root.find(ns + "g")
    groups = {
        group.find(ns + "title").text: group
        for group in graph.findall(ns + "g")
        if group.find(ns + "title") is not None
    }
    replacements = dict(zip(DESCRIPTIONS[stage], descriptions))
    replacements[STAGES[stage][0]] = title
    replacements["Orange boxes: focus of this phase. Gray boxes: not connected to this KB."] = (
        "Orange: new build. Faded: reused. Covered: not used by this KB."
    )
    for text in graph.findall(ns + "text"):
        if text.text in replacements:
            is_legend = text.text.startswith("Orange boxes:")
            text.text = replacements[text.text]
            if not is_legend:
                text.set("text-anchor", "middle")
                text.set("x", str(float(root.attrib["viewBox"].split()[2]) / 2 - 25.2))

    for text in graph.iter(ns + "text"):
        if text.text == "Connected":
            text.text = "Reused from Part 1"
        elif not complete and text.text and " connected source definitions" in text.text:
            text.text = text.text.replace(" connected", " planned")
        elif not complete and text.text == "Live source":
            text.text = "Planned live connection" if part in (2, 3) else "Existing source definition"

    for name, group in groups.items():
        kind = group.attrib.get("class")
        if kind == "cluster":
            group.set("opacity", "0.45")
        elif kind == "node":
            group.set("opacity", "0.4")
            shape = group.find(ns + "path")
            shape.set("fill", "#F5F6F8")
            shape.set("stroke", "#B9C1CA")
        elif kind == "edge":
            group.set("opacity", "0.15")
    for name in config["focus"]:
        group = groups[name]
        group.set("opacity", "1" if complete else "0.65")
        group.set("data-build-state", "completed" if complete else "planned")
        shape = group.find(ns + "path")
        shape.set("fill", "#FFF0D8")
        shape.set("stroke", ORANGE)
        shape.set("stroke-width", "3")
        if not complete:
            shape.set("stroke-dasharray", "8,5")
    for name in config["new_edges"]:
        groups[name].set("opacity", "1" if complete else "0.12")
    for name in ("entra", "notebook->entra"):
        groups[name].set("opacity", "0.55")

    for cluster, caption in config["covers"].items():
        shape = groups[cluster].find(ns + "path")
        coordinates = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", shape.attrib["d"])]
        left, right = min(coordinates[::2]), max(coordinates[::2])
        top, bottom = min(coordinates[1::2]), max(coordinates[1::2])
        cover = ET.SubElement(graph, ns + "g", {"data-part-cover": cluster})
        ET.SubElement(cover, ns + "rect", {
            "x": str(left), "y": str(top), "width": str(right - left),
            "height": str(bottom - top), "rx": "12",
            "fill": "#F4F5F7", "stroke": "#D8DDE3",
        })
        text = ET.SubElement(cover, ns + "text", {
            "x": str((left + right) / 2), "y": str((top + bottom) / 2),
            "text-anchor": "middle", "font-family": "Segoe UI",
            "font-size": "15", "fill": "#687787",
        })
        text.text = caption
    root.set("aria-label", title + ". " + " ".join(descriptions) + " Not a live deployment status.")
    return ET.tostring(root, encoding="unicode")


def render_part_reveals():
    for part in PART_REVEALS:
        for complete, suffix in ((False, "before"), (True, "after")):
            name = f"part{part}-{suffix}"
            svg = build_part_reveal(part, complete)
            (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
            (OUT / f"{name}.png").write_bytes(resvg_py.svg_to_bytes(svg_string=svg, width=1800, dpi=96))
            print(f"Rendered {name}: staged SVG and PNG")


def main():
    check_icons()
    dot = shutil.which("dot")
    if dot is None:
        candidate = Path(r"C:\Program Files\Graphviz\bin\dot.exe")
        if not candidate.is_file():
            raise FileNotFoundError("Graphviz dot.exe is required. See docs/visual-guide.md.")
        dot = str(candidate)
    for icon in ICONS.glob("*.svg"):
        icon.with_suffix(".png").write_bytes(resvg_py.svg_to_bytes(svg_path=str(icon), width=112, height=112))
    for stage in ["overview", *STAGES]:
        name = f"azure-{stage}"
        source = build(stage)
        result = subprocess.run(
            [dot, "-Tsvg"], input=source, text=True, capture_output=True, cwd=OUT, check=True, timeout=30,
        )
        if result.stderr.strip():
            raise RuntimeError(f"Graphviz reported a rendering problem for {name}: {result.stderr}")
        svg = route_service_connections(result.stdout)
        for icon in ICONS.glob("*.svg"):
            uri = "data:image/svg+xml;base64," + base64.b64encode(icon.read_bytes()).decode("ascii")
            svg = svg.replace(f'xlink:href="icons/{icon.stem}.png"', f'xlink:href="{uri}"')
        if re.search(r'xlink:href="(?!data:)', svg):
            raise ValueError(f"{name} is not self-contained")
        description = (
            " ".join(DESCRIPTIONS[stage]) + " Service architecture with official Azure, Fabric and Entra icons. "
            "Separate local device, Azure resource group, Fabric workspace, Microsoft 365 and identity boundaries. "
            "Arrows point from caller to dependency. This is not a live deployment status."
        )
        svg = svg.replace("<svg ", '<svg role="img" aria-label="' + escape(description) + '" ', 1)
        (OUT / f"{name}.dot").write_text(source, encoding="utf-8")
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        (OUT / f"{name}.png").write_bytes(resvg_py.svg_to_bytes(svg_string=svg, width=1800, dpi=96))
        print(f"Rendered {name}: SVG, PNG, editable Graphviz source")
    render_part1_reveals()
    render_part_reveals()
    (OUT / "descriptions.json").write_text(
        json.dumps({stage: " ".join(lines) for stage, lines in DESCRIPTIONS.items()}, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT / "walkthroughs.json").write_text(
        json.dumps(WALKTHROUGHS, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    main()
