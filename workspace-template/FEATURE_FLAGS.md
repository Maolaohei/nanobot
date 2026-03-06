# FEATURE_FLAGS.md — 阶段A默认开关（模板）

rollout:
  parallel_framework_enabled: true
  parallel_framework_gray: 0.30

stability:
  filter_error_turns: true
  retry_policy:
    timeout: {retries: 1, wait_seconds: 3}
    rate_limit_429: {retries: 1, wait_seconds: 10}
    server_5xx: {retries: 1, wait_seconds: 5}
    auth_401_403: {retries: 0}
    not_found_404: {retries: 0}
    antibot_412: {retries: 0}
  provider_healthcheck: true
  auto_provider_failover: true

pipeline_parallel:
  enabled: true
  composite_find_and_get: true
  platform_limits:
    pixiv: {max_concurrency: 6, rpm: 60}
    bilibili: {max_concurrency: 2, rpm: 30}
    web: {max_concurrency: 4, rpm: 60}
  fallback_chain:
    pixiv: [pixiv-pro, gallery-dl, notify]
    web: [content-reader, browser-helper, scrapling, web_fetch, notify]
    bilibili: [bilibili-downloader, notify]

pixiv_quality:
  min_bookmarks: 10000
  ai_soft_filter: true
  allow_half_ai: false
  nsfw_guard: true
  query_expansion: ["水着","泳装","bikini"]

multimodal_routing:
  image_to_image_recognizer: true
  video_to_ffmpeg: true
  disable_llm_multimodal: true

source_governance:
  disable_daily_briefing: true
  trusted_sources_file: ./TRUSTED_SOURCES.md

bilibili_antibot:
  no_retry_status: [401,403,404,412]
  fixed_ua: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

persona_guard:
  enabled: true
  partition_protection: true
  temp_toggle_command: "/persona off 60m"

observability_cost:
  minimal_metrics: true
  telegram_reports: {daily: true, weekly: true}
