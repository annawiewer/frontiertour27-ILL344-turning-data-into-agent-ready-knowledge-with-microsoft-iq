# Workshop notebooks

Open the notebooks in order using the lab's Python `.venv` kernel. Start with the [lab setup](../instructions/overview.md).

Start with the [visual learning path](notebooks/README.md) to understand the services, their roles, and the six KB variants across five parts before running code. The [overall service map](../img/architecture/azure-overview.svg) separates remote evidence, Search retrieval, model calls, and the local agent.

| Notebook | What changes | Evidence to inspect |
| --- | --- | --- |
| [Part 1](notebooks/part1-standard-foundry-iq-kb.ipynb) | Upload policy, connect existing indexes, create policy and three-source KBs | Ingestion read-back, source membership, policy and document citations |
| [Part 2](notebooks/part2-fabric-iq-to-kb.ipynb) | Create a separate Fabric-enabled KB | Ontology relationships, delegated source access, Fabric references |
| [Part 3](notebooks/part3-work-iq-to-kb.ipynb) | Create a separate Work IQ-enabled KB | Identity prerequisites, workplace evidence, approved versus discussed commitments |
| [Part 4](notebooks/part4-work-iq-fabric-iq-to-kb.ipynb) | Combine all five sources in another KB | Actual source activity and cross-source grounding |
| [Part 5](notebooks/part5-agent-framework-mcp.ipynb) | Create an extractive KB over the Part 1 sources and call it from a local agent | MCP tool calls and agent-synthesized citations |

Each notebook includes an architecture map, read-only configuration checkpoints, portal navigation, and a Source Hunt. The maps describe intended wiring. The checkpoint cells verify actual configuration. Retrieval activity and references verify what happened for one query.

`notebooks/lab_visuals.py` renders the shared checkpoint tables and evidence cards. Raw activity and reference JSON remains available in expandable details. It does not create resources or query protected source content.

Part 2 uses device-code sign-in and never opens a browser automatically. Run Step 2, copy its verification URL into a new tab in the intended browser profile, enter the code from that cell, and sign in with the account that has Fabric workspace access. Keep the cell running until it reports `Acquired token for logged-in user`. Do not share the code, and clear cell outputs before sharing the notebook. Rerun Step 2 if the code expires. Tenant-policy failures are reported without silently switching authentication methods.

After updating the notebook, stop any pending sign-in, reopen it, restart the kernel, and rerun Steps 1 and 2. The tenant remains `FABRIC_TENANT_ID`, falling back to `AZURE_TENANT_ID`. The former `AZURE_AUTH_EDGE_PROFILE` setting is no longer used.

See the [visual field guide](../docs/visual-guide.md) for architecture assets, portal observations, screenshot capture guidance, and offline checks.
