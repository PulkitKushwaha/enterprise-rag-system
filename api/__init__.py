# Production API layer
#
# FastAPI application using patterns from production-rag-api:
#   - Factory function (create_app()) for testability
#   - lru_cache singletons for pipeline + guardrails
#   - JWT + API key authentication
#   - Sliding window rate limiting
#   - SSE streaming endpoint
#   - Prometheus metrics + structured logging
#   - Multi-stage Docker build
#
# Endpoints:
#   POST /api/v1/query          — JSON response
#   POST /api/v1/query/stream   — SSE streaming
#   GET  /api/v1/health         — liveness
#   GET  /api/v1/ready          — readiness
#   GET  /api/v1/metrics        — Prometheus