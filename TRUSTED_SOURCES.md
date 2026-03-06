# TRUSTED_SOURCES.md — 可信源清单（示例）

- 官方博客 / 文档：
  - OpenAI, Anthropic, Google, Meta, Apple, Microsoft 官方技术博客
  - Cloudflare, Fastly, AWS, GCP, Azure 官方公告
- 开源社区：
  - GitHub 官方公告与安全通告
  - Debian/Ubuntu 安全公告
- 媒体与聚合：
  - Reuters, AP, Bloomberg Tech, The Verge
  - Hacker News、Lobsters（仅原链接）

路由：优先 content-reader，遇反爬/JS 渲染转 browser-helper，仍失败再降级通用抓取。
