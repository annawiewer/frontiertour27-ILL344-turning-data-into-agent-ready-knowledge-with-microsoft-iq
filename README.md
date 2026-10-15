<a name="start-building"></a>

<p align="center">
<img src="img/banner-frontier-tour-27.png" alt="Microsoft Frontier Tour 2027" width="100%"/>
</p>

# [Microsoft Frontier Tour 2027](https://aitour.microsoft.com)

## 🔥 ILL344: Turning data into agent-ready knowledge with Microsoft IQ

### Session description

Use Foundry IQ to build a multi-source knowledge base with agentic retrieval, Fabric IQ to retrieve structured data from OneLake, and Work IQ to include organizational context. Build an agent that uses their combined retrieval power to reason across files, data, and work signals.

### 🚀 Getting started

#### In a guided session

If you're following along during a live session:

1. Open the lab environment and sign in with the provided credentials.
2. Follow the setup guidance in [`instructions/overview.md`](instructions/overview.md).
3. Open [`src/notebooks/`](src/notebooks/), start with [`part1-standard-foundry-iq-kb.ipynb`](src/notebooks/part1-standard-foundry-iq-kb.ipynb), and work through all five notebooks sequentially.

#### On your own

If you're learning at your own pace:

1. Clone this repository.
2. Provision the required resources by following the [self-deployment guide](deploy_yourself.md).
3. Follow [`instructions/overview.md`](instructions/overview.md), then work through all five notebooks in [`src/notebooks/`](src/notebooks/) sequentially.

### 🎯 Learning outcomes

By the end of this session, you will be able to:

- Build a multi-source knowledge base over indexed enterprise content using Foundry IQ (Azure AI Search) agentic retrieval.
- Extend a knowledge base with Fabric IQ and Work IQ knowledge sources.
- Build a Python agent using Microsoft Agent Framework with answers grounded in a Foundry IQ knowledge base.

### 💻 Technologies used

- Foundry IQ (Azure AI Search)
- Azure OpenAI (`gpt-5.4` and `text-embedding-3-large`)
- Model Context Protocol (MCP)
- Microsoft Fabric IQ and Work IQ
- Python and Jupyter Notebooks

### 📚 Continue your learning

Pick your next step based on your learning style:

| Resource | What you'll get |
|----------|-----------------|
| **[Session Recording](https://aka.ms/ft27/ill344/youtube)** | A recording of session ILL344 by the session creator |
| **[Foundry IQ (Azure AI Search) documentation](https://learn.microsoft.com/azure/search/)** | Explore the full capabilities of Foundry IQ (Azure AI Search) |
| **[Create a knowledge base](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-knowledge-base)** | Follow the steps to create and configure a knowledge base |
| **[Design an index for agentic retrieval](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-index)** | Learn best practices for structuring data for agentic retrieval |
| **[Microsoft Learn](https://learn.microsoft.com)** | Official documentation and guided learning paths on these topics |
| **[Frontier Tour 2027 Resource Center](https://aka.ms/FrontierTour27)** | Additional session repos and materials from Frontier Tour 2027 |
| **[Microsoft Foundry Community](https://aka.ms/MicrosoftFoundryDiscord-ft27)** | Connect with other learners and experts in our Discord community |

### 🌟 Microsoft Learn MCP Server

<!-- Remove this section if the Microsoft Learn MCP Server is not relevant to the session. -->

The Microsoft Learn MCP Server gives your AI agent direct access to Microsoft's official documentation — grounded, up-to-date answers about the topics in this session.

**GitHub Copilot CLI** — Install with:

```shell
copilot plugin install microsoftdocs/mcp
```

**VS Code** — One-click install:  
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_Microsoft_Learn_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=microsoft-learn&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Flearn.microsoft.com%2Fapi%2Fmcp%22%7D)

For more information, visit the [Learn MCP Server repo](https://aka.ms/learnmcp).

### 👥 Content owners

<table>
<tr>
    <td align="center"><a href="https://github.com/pamelafox">
        <img src="https://github.com/pamelafox.png" width="100px;" alt="Pamela Fox"/><br />
        <sub><b>Pamela Fox</b></sub></a><br />
            <a href="https://github.com/pamelafox" title="talk">📢</a>
    </td>
    <td align="center"><a href="https://github.com/aycabas">
        <img src="https://github.com/aycabas.png" width="100px;" alt="Ayca Bas"/><br />
        <sub><b>Ayca Bas</b></sub></a><br />
            <a href="https://github.com/aycabas" title="talk">📢</a>
    </td>
</tr></table>

### Deliver this session

Presenters and re-delivery partners can find the deck, recordings, presenter
notes, and delivery guidance in [`delivery-resources/`](delivery-resources/README.md).

### ⚖️ Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.

Any use of third-party trademarks or logos are subject to those third-party's policies.
