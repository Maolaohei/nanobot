# OpenTelemetry tracing and coverage

This PR introduces optional OpenTelemetry tracing initialization and CI coverage reporting.

What changed
- utils/tracing.py: Safe, env-gated setup_tracing(service_name)
- __main__.py: initialize structured logging + optional tracing on startup
- CI: run pytest via coverage, upload coverage.xml to Codecov on PRs
- tests: add minimal tests for tracing init switches

How to enable tracing
- Default is off. Set environment variable:
  - NANOBOT_TRACING_ENABLED=true
  - Optional: OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
  - Optional: OTEL_TRACES_EXPORTER=otlp|console (auto console if no endpoint)
  - Optional: OTEL_TRACES_SAMPLER_RATIO=1.0

Notes
- No hard dependency; if `opentelemetry-sdk` is absent, code logs a warning and continues.
- Coverage reporting requires CODECOV_TOKEN secret on the repo for PRs.
