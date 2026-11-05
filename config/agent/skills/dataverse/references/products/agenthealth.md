### **AgentHealth**
**Database:** `agenthealth_db`
**Schemas:** `marts`, `dataverseagent_marts`
**Maturity:** AI Experimental

Unified AI Agent Health Monitoring framework providing centralized tracking of AI agent performance, cost, and usage metrics through Langfuse trace data integration.

**Primary use cases:** AI agent performance monitoring, LLM cost analysis, user feedback tracking, error analysis, data product usage patterns, and agent health dashboards.

**When to route here:** Queries about AI agent metrics, Langfuse traces, LLM costs, agent latency, user feedback on AI agents, agent errors, throughput, or agent operational health.

**Data Scope & Coverage:**

*What IS in AgentHealth:*
- AI agent performance metrics (latency, response times, throughput, error rates)
- LLM cost data per request
- User feedback (positive/negative flags and comments)
- User questions and queries submitted to agents
- Data product access patterns
- Per-agent and per-data-product breakdowns

*What IS NOT in AgentHealth:*
- Actual AI agent responses or generated content
- Agent configuration or deployment settings
- Infrastructure metrics (CPU, memory, uptime) → Use infrastructure monitoring tools
- User authentication or profile data → Use **RoverPeople**
- Business transaction data → Use appropriate business data products

**🔑 KEY ROUTING RULES:**
- **"Show metrics for [AGENT-NAME]"** / **"How is [AGENT] performing?"** / **"LLM costs for [AGENT]"** → `agenthealth_db.MARTS`
- **"Compare agent performance"** → `agenthealth_db.MARTS` (multiple agent tables)
- **"What questions are users asking about my data product?"** / **"Feedback on my data product"** → `agenthealth_db.DATAVERSEAGENT_MARTS` (RLS-restricted, Dataverse Agent only)

---

---
## 🔗 Aggregate Data Products

These data products integrate and transform data from multiple source-aligned products to provide comprehensive cross-domain analytics.
