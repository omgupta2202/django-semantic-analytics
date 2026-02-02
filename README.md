# django-semantic-analytics

Sophisticated Semantic RAG Middleware for production-grade Text-to-SQL in Django.

## Overview
`django-semantic-analytics` moves beyond basic "Text-to-SQL" by using **Semantic Atoms**. These are pre-defined, trusted SQL snippets that represent business logic (Metrics, Dimensions, Joins). The LLM acts as an assembler, combining these fragments rather than hallucinating complex joins from scratch.

## Key Components
- **The Registry**: Store `SemanticAtom` objects with vector embeddings (`pgvector`).
- **The Retriever**: Finds atoms relevant to user questions and recursively pulls dependencies (e.g., if a Metric requires a specific JOIN).
- **The Assembler**: A Strict-Mode prompt that forces the LLM to use only provided atoms.
- **The Bouncer**: Security layer using `sqlglot` to verify queries are `SELECT`-only and enforces limits.
- **The Fix Workflow**: An admin-driven loop to review failed queries and save corrected SQL as `VerifiedQuery` (Golden Queries).

## Requirements
- Django >= 4.2
- PostgreSQL with `pgvector` extension
- `sqlglot`
- `openai`

## Setup
1. Add `django_semantic_analytics` to `INSTALLED_APPS`.
2. Configure settings:
   ```python
   OPENAI_API_KEY = "your-key"
   SEMANTIC_ANALYTICS_READ_REPLICA = "read_only_db" # Optional
   ```
3. Run migrations.

## Usage
```python
from django_semantic_analytics.services import SemanticAnalyticsService

service = SemanticAnalyticsService()
results = service.ask("What was the daily practice score for John Doe yesterday?")
```
