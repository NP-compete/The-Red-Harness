### **DataverseHelp**
**Database:** `dataversehelp_db`
**Schema:** `dataversehelp_marts`
**Maturity:** AI Experimental

Dataverse platform documentation knowledge base. Contains chunked and embedded content from the official Dataverse documentation site (dataverse.pages.redhat.com) and supporting GitLab repositories — covering how to explore data, build data products, build AI tools, platform administration, governance, and community resources.

**⚠️ THIS IS A DOCUMENTATION SEARCH PRODUCT, NOT A BUSINESS DATA PRODUCT.** It returns text chunks from platform documentation. It has no business metrics, no transactional data, no customer/employee/financial records.

**Primary use cases:** Answering "how do I" questions about the Dataverse platform — how to request access, how to build data products, how to set up tooling (dbt, Fivetran, Snowflake, Astro), AI development guides, governance policies, and Dataverse glossary lookups.

**When to route here:** Queries about Dataverse platform documentation, "how do I" questions about Dataverse processes, data product development guides, AI tool development, MCP server setup, Dataverse Agent usage instructions, Snowflake access requests, dbt setup, Fivetran configuration, data governance policies, unstructured data pipelines, InnerSource contribution, community resources, or Dataverse glossary terms.

**Documentation Coverage (from dataverse.pages.redhat.com):**
- **Use Data** (8 pages): Discovering data products, requesting access, using the Dataverse Agent, querying Snowflake, connecting BI tools (Tableau, Python, CRMA), MCP and Cursor setup
- **Build Data Products** (~30 pages): Source-aligned and aggregate product development, dbt, Fivetran, Snowpipe, Astro, GitLab CI/CD, governance & compliance, AI readiness, operations, lifecycle, InnerSource
- **Build AI Tools** (8 pages): MCP servers, AI agents (LangGraph), path-to-production (OpenShift, security review), observability (Langfuse), unstructured data / RAG pipelines
- **Platform** (shared): Snowflake administration (naming conventions, schema management, warehouse sizing), dbt platform config, Fivetran logs, Basecamp (SCIM), release notes
- **Community & Glossary**: Slack channels, TOC governance, mailing lists, InnerSource contribution guides, Dataverse-specific terminology

**❌ DO NOT route here for:**
- **Any business data query** (revenue, bookings, sales, costs, headcount, expenses, pipeline, forecasts) → Use the appropriate business data product (Bookingsmaster, RevenueMaster, ExpenseMaster, RoverPeople, etc.)
- **AI agent performance metrics** (latency, errors, LLM costs, Langfuse traces, token usage) → Use **AgentHealth**
- **Specific data product schema questions** (column definitions, table structures, which columns to use) → Use the relevant data product's own README guidance via the normal get_sql pipeline
- **Jira project management data** → Use **JIRA**
- **Real-time platform health or system status** → Use infrastructure monitoring tools
- **ANY query asking for numbers, metrics, counts, sums, averages, trends, or reports** → This is a text search knowledge base, not an analytics product

**🔑 KEY ROUTING RULES:**
- **"How do I request access to a data product?"** / **"How do I build a data product?"** / **"What is Dataverse?"** → `dataversehelp_db.DATAVERSEHELP_MARTS`
- **"How do I set up dbt?"** / **"How do I connect Tableau to Snowflake?"** / **"What is a source-aligned product?"** → `dataversehelp_db.DATAVERSEHELP_MARTS`
- **"How do I build an MCP server?"** / **"How do I deploy an AI agent?"** / **"What is Langfuse?"** → `dataversehelp_db.DATAVERSEHELP_MARTS`
- **"What are the Dataverse naming conventions?"** / **"What Slack channels exist for Dataverse?"** → `dataversehelp_db.DATAVERSEHELP_MARTS`
- **"What are the data governance policies?"** / **"How do I contribute via InnerSource?"** → `dataversehelp_db.DATAVERSEHELP_MARTS`

**⚠️ COLLISION PREVENTION — DO NOT confuse these:**
- "How do I **use** bookings data?" → **DataverseHelp** (asking about platform process)
- "Show me **bookings** for Q2" → **Bookingsmaster** (asking for business data)
- "How do I **set up** dbt?" → **DataverseHelp** (asking about tooling setup)
- "What is the **dbt model** for revenue?" → **RevenueMaster** (asking about specific data product)
- "How do I **request access** to a data product?" → **DataverseHelp** (platform process)
- "Show me **access** patterns for our customers" → **Bookingsmaster** or other (business analytics)

---
---

## 📋 Getting Started
