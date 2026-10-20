"""Read-only checkpoints and evidence views for the Caldova lab notebooks."""

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

from IPython.display import HTML, SVG, display


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROLES = {
    "file-docs-knowledge-source": ("file", "Purchasing policy", None),
    "supplier-evidence-knowledge-source": ("searchIndex", "Operational evidence", "supplier-evidence"),
    "sourcing-documents-knowledge-source": ("searchIndex", "Approved commitments", "sourcing-documents"),
    "fabric-ontology-knowledge-source": ("fabricOntology", "Structured relationships", None),
    "workiq-knowledge-source": ("workIQ", "Current workplace discussion", None),
}
STAGES = ("start", "policy", "documents", "fabric", "workiq", "combined", "agent")


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    head = "".join(f"<th scope='col'>{_text(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_text(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _details(title: str, value: object) -> str:
    raw = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    return f"<details><summary>{_text(title)}</summary><pre>{_text(raw)}</pre></details>"


def _link(url: str, label: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return _text(label) + " (no safe HTTPS link)"
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return _text(label) + " (no safe HTTPS link)"
    return f"<a href='{_text(url)}' target='_blank' rel='noopener noreferrer'>{_text(label)}</a>"


def show_architecture(stage: str) -> None:
    """Display an expected architecture, never a live health assertion."""
    if stage not in STAGES:
        raise ValueError(f"Unknown architecture stage: {stage}")
    descriptions = json.loads(
        (REPO_ROOT / "img" / "architecture" / "descriptions.json").read_text(encoding="utf-8")
    )
    walkthroughs = json.loads(
        (REPO_ROOT / "img" / "architecture" / "walkthroughs.json").read_text(encoding="utf-8")
    )
    steps = "".join(f"<li>{_text(step)}</li>" for step in walkthroughs[stage])
    display(SVG(filename=str(REPO_ROOT / "img" / "architecture" / f"azure-{stage}.svg")))
    display(HTML(
        f"<p><strong>Architecture in brief:</strong> {_text(descriptions[stage])}</p>"
        f"<p><strong>Step by step:</strong></p><ol>{steps}</ol>"
        "<p><strong>Architecture guide, not live status.</strong> "
        "Highlighted connections are the target for this stage. "
        "Use the read-back checkpoints and query evidence below to verify your environment.</p>"
    ))


def _source_rows(index_client, names: Sequence[str]) -> list[tuple[str, str, str, str]]:
    rows = []
    for name in names:
        source = index_client.get_knowledge_source(name)
        expected_kind, role, expected_index = SOURCE_ROLES[name]
        if source.kind != expected_kind:
            raise RuntimeError(f"{name}: expected kind {expected_kind}, got {source.kind}")
        target = "Remote, queried with user authorization" if expected_kind in {
            "fabricOntology", "workIQ"
        } else "Uploaded policy, ingestion checked separately"
        if expected_index:
            target = source.search_index_parameters.search_index_name
            if target != expected_index:
                raise RuntimeError(f"{name}: expected index {expected_index}, got {target}")
        rows.append((name, str(source.kind), role, target))
    return rows


def verify_sources(index_client, names: Sequence[str]) -> None:
    """Read source definitions from Search without creating or changing anything."""
    rows = _source_rows(index_client, names)
    display(HTML(
        "<h4>Source definitions verified by read-back</h4>"
        + _table(("Source", "Kind", "Evidence role", "Target"), rows)
        + "<p>This confirms configuration only. It does not prove ingestion or retrieval succeeded.</p>"
    ))


def verify_knowledge_base(
    index_client,
    name: str,
    expected_sources: Sequence[str],
    *,
    extractive: bool = False,
) -> None:
    """Verify exact KB membership and the synthesis boundary using service read-back."""
    kb = index_client.get_knowledge_base(name)
    actual = [source.name for source in kb.knowledge_sources]
    if sorted(actual) != sorted(expected_sources):
        raise RuntimeError(
            f"{name}: source membership differs. Expected {sorted(expected_sources)}, got {sorted(actual)}"
        )
    expected_mode = "extractiveData" if extractive else "answerSynthesis"
    if kb.output_mode != expected_mode:
        raise RuntimeError(f"{name}: expected output mode {expected_mode}, got {kb.output_mode}")
    if extractive and kb.models:
        raise RuntimeError(f"{name}: the extractive lab KB must not have an attached model")
    if not extractive and not kb.models:
        raise RuntimeError(f"{name}: the synthesis lab KB needs an attached model")
    if extractive:
        effort = kb.retrieval_reasoning_effort
        kind = effort.get("kind") if isinstance(effort, Mapping) else getattr(effort, "kind", None)
        if kind != "minimal":
            raise RuntimeError(f"{name}: the extractive lab KB must use minimal reasoning")
    rows = _source_rows(index_client, actual)
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    display(HTML(
        f"<h4>Configuration verified: {_text(name)}</h4>"
        f"<p>Read from Search at {_text(checked_at)}. Output mode: "
        f"<code>{_text(kb.output_mode)}</code>. Attached models: {len(kb.models or [])}.</p>"
        + _table(("Connected source", "Kind", "Evidence role", "Target"), rows)
        + "<p><strong>Next check:</strong> run the query and inspect its activity and references. "
        "A configured connection is not proof of successful source access.</p>"
    ))


def show_file_ingestion(index_client, name: str) -> None:
    """Show server-reported ingestion information without guessing readiness."""
    status = index_client.get_knowledge_source_status(name)
    files = list(index_client.list_knowledge_source_files(name))
    rows = [(f.file_name, f.file_size_bytes, f.error_message or "No file error reported") for f in files]
    display(HTML(
        f"<h4>File ingestion: {_text(status.synchronization_status)}</h4>"
        + _table(("Uploaded file", "Bytes", "Reported error"), rows)
        + "<p>Upload acceptance and an active source do not guarantee that every file is searchable yet. "
        "The policy query and its file references provide the end-to-end check. "
        "If processing is still underway, rerun this read-only cell before querying.</p>"
    ))
    if not files:
        raise RuntimeError(f"No uploaded files were returned for {name}")
    if any(f.error_message for f in files):
        raise RuntimeError(f"File processing failed for {name}. See the reported errors above.")


def show_portal_links(
    search_endpoint: str,
    *,
    search_resource_id: str = "",
    workspace_id: str = "",
    ontology_id: str = "",
    app_id: str = "",
) -> None:
    """Build links locally. Never include API keys or user tokens."""
    service = urlsplit(search_endpoint).hostname
    if not service:
        raise ValueError("Search endpoint must include a hostname")
    search_url = "https://portal.azure.com"
    instruction = f"Select {service.split('.')[0]}, then Agentic retrieval."
    if search_resource_id:
        if not search_resource_id.startswith("/subscriptions/"):
            raise ValueError("Search resource ID must start with /subscriptions/")
        search_url += "/#resource" + quote(search_resource_id, safe="/")
    links = [
        f"<li>{_link(search_url, 'Azure Portal: your Search service')}. {_text(instruction)}</li>",
        f"<li>{_link('https://ai.azure.com', 'Microsoft Foundry: inspect model deployments')}</li>",
    ]
    if workspace_id:
        workspace_url = f"https://app.fabric.microsoft.com/groups/{quote(workspace_id, safe='')}"
        links.append(f"<li>{_link(workspace_url + '/list?experience=fabric', 'Fabric: your workspace')}</li>")
        if ontology_id:
            links.append(
                f"<li>{_link(workspace_url + '/ontologies/' + quote(ontology_id, safe=''), 'Fabric: your ontology')}</li>"
            )
    if app_id:
        app_url = (
            "https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/"
            "ApplicationMenuBlade/~/Overview/appId/" + quote(app_id, safe="")
        )
        links.append(f"<li>{_link(app_url, 'Entra: Work IQ app registration')} (if permitted)</li>")
    display(HTML(
        "<h4>Open your resources</h4><ul>" + "".join(links) + "</ul>"
        "<p>Links use your local configuration and current browser identity. "
        "Select the lab tenant and subscription. If Search opens the portal home page, "
        "find the service by the name above. Optionally set AZURE_SEARCH_RESOURCE_ID "
        "locally for a direct resource link. Work IQ configuration itself is SDK/API-only.</p>"
    ))


def show_activity(activities: Sequence[Mapping[str, object]]) -> None:
    """Render the actual activity records, including partial source failures."""
    rows = []
    for item in activities:
        error, warning = item.get("error"), item.get("warning")
        outcome = "Failed" if error else "Warning" if warning else "Observed"
        duration = item.get("elapsedMs")
        rows.append((
            item.get("id", "?"),
            item.get("type", "Unknown"),
            item.get("knowledgeSourceName", "KB processing"),
            f"{duration} ms" if duration is not None else "Not reported",
            outcome,
            json.dumps(error, ensure_ascii=False) if error else warning or "",
        ))
    display(HTML(
        "<h4>What actually ran</h4>"
        + (_table(("Activity", "Operation", "Source", "Duration", "Outcome", "Detail"), rows)
           if rows else "<p><strong>No activity returned. Source execution is unverified.</strong></p>")
        + "<p>Rows follow the returned activity order, not a serial timeline. "
        "Operations can overlap. Observed means an activity was reported, not that it supplied evidence.</p>"
        + _details("Raw activity JSON", activities)
    ))


def _origin(reference: Mapping[str, object], activities: Sequence[Mapping[str, object]]) -> str:
    activity_id = reference.get("activitySource")
    for item in activities:
        if activity_id is not None and str(item.get("id")) == str(activity_id):
            return str(item.get("knowledgeSourceName") or "Unresolved source")
    return "Unresolved source"


def _reference_preview(reference: Mapping[str, object]) -> tuple[str, str, str]:
    data = reference.get("sourceData")
    target = str(reference.get("citationUrl") or "")
    if not isinstance(data, Mapping):
        return str(reference.get("docName") or "Retrieved reference"), "", target
    title = str(data.get("title") or reference.get("docName") or reference.get("type", "Reference"))
    snippet = str(data.get("snippet") or data.get("chunk") or data.get("fabricAnswer") or "")
    parts = data.get("parts")
    if isinstance(parts, list):
        for part in parts:
            if not isinstance(part, Mapping):
                continue
            if not snippet and isinstance(part.get("text"), str):
                snippet = part["text"]
            citations = part.get("data")
            if isinstance(citations, Mapping):
                for citation in citations.values():
                    if isinstance(citation, Mapping) and isinstance(citation.get("targetLink"), str):
                        target = citation["targetLink"]
                        break
    pages = data.get("page_number_from")
    if pages is not None:
        title += f" (pages {pages} to {data.get('page_number_to', pages)})"
    return title, snippet[:500], target


def show_references(
    references: Sequence[Mapping[str, object]],
    activities: Sequence[Mapping[str, object]],
    expected_sources: Sequence[str],
) -> None:
    """Keep configuration, attempted retrieval and returned evidence distinct."""
    rows = []
    for name in expected_sources:
        calls = [a for a in activities if a.get("knowledgeSourceName") == name]
        evidence = [r for r in references if _origin(r, activities) == name]
        if any(a.get("error") for a in calls):
            state = "Source error reported"
        elif any(a.get("warning") for a in calls):
            state = "Warning reported, inspect activity"
        elif evidence:
            state = "Evidence returned"
        elif calls:
            state = "Called, no linked references"
        else:
            state = "Not observed, not necessarily broken"
        rows.append((name, SOURCE_ROLES[name][1], len(calls), len(evidence), state))
    cards = []
    for reference in references:
        title, snippet, target = _reference_preview(reference)
        origin = _origin(reference, activities)
        role = SOURCE_ROLES[origin][1] if origin in SOURCE_ROLES else "Source attribution unresolved"
        cards.append(
            "<article style='border:1px solid #888;padding:12px;margin:8px 0'>"
            f"<strong>Reference {_text(reference.get('id', '?'))}: {_text(title)}</strong>"
            f"<p>{_text(role)} | {_text(reference.get('type', 'Unknown'))}<br>{_text(origin)}</p>"
            f"<p>{_text(snippet) if snippet else 'Inspect the structured evidence in Raw references JSON.'}</p>"
            + (_link(target, "Open supporting source") if target else "")
            + "</article>"
        )
    display(HTML(
        "<h4>Which sources supplied evidence?</h4>"
        + _table(("Source", "Evidence role", "Activities", "References", "This query"), rows)
        + ("".join(cards) if cards else "<p><strong>No references returned. Grounding is unverified.</strong></p>")
        + "<p>These are retrieved references, not a claim that every item was cited in the final answer. "
        "Compare answer citation markers with reference IDs. A source not selected for this question "
        "can still be correctly configured.</p>"
        + _details("Raw references JSON", references)
    ))
