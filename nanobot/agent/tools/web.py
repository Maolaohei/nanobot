"""Web tools: web_search and web_fetch."""

import html
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

from nanobot.agent.tools.base import Tool
+from nanobot.utils.http import HttpClientFactory, request as http_request

# Shared constants
-USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
+USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
 MAX_REDIRECTS = 5  # Limit redirects to prevent DoS attacks


 def _strip_tags(text: str) -> str:
     """Remove HTML tags and decode entities."""
     text = re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.I)
     text = re.sub(r'<style[\s\S]*?</style>', '', text, flags=re.I)
     text = re.sub(r'<[^>]+>', '', text)
     return html.unescape(text).strip()
@@
 class WebSearchTool(Tool):
@@
     def __init__(self, api_key: str | None = None, max_results: int = 5, proxy: str | None = None):
-        self._init_api_key = api_key
-        self.max_results = max_results
-        self.proxy = proxy
+        self._init_api_key = api_key
+        self.max_results = max_results
+        self.proxy = proxy
+        self._http_factory = HttpClientFactory(proxy=proxy, rate_limit=60)
@@
     async def execute(self, query: str, count: int | None = None, **kwargs: Any) -> str:
@@
-        try:
-            n = min(max(count or self.max_results, 1), 10)
-            logger.debug("WebSearch: {}", "proxy enabled" if self.proxy else "direct connection")
-            async with httpx.AsyncClient(proxy=self.proxy) as client:
-                r = await client.get(
-                    "https://api.search.brave.com/res/v1/web/search",
-                    params={"q": query, "count": n},
-                    headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
-                    timeout=10.0
-                )
-                r.raise_for_status()
+        try:
+            n = min(max(count or self.max_results, 1), 10)
+            logger.debug("WebSearch: {}", "proxy enabled" if self.proxy else "direct connection")
+            client = self._http_factory.create()
+            r = await http_request(
+                "GET",
+                "https://api.search.brave.com/res/v1/web/search",
+                client=client, headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
+                params={"q": query, "count": n},
+            )
@@
 class WebFetchTool(Tool):
@@
-    def __init__(self, max_chars: int = 50000, proxy: str | None = None):
-        self.max_chars = max_chars
-        self.proxy = proxy
+    def __init__(self, max_chars: int = 50000, proxy: str | None = None):
+        self.max_chars = max_chars
+        self.proxy = proxy
+        self._http_factory = HttpClientFactory(proxy=proxy, rate_limit=60)
@@
-        try:
-            logger.debug("WebFetch: {}", "proxy enabled" if self.proxy else "direct connection")
-            async with httpx.AsyncClient(
-                follow_redirects=True,
-                max_redirects=MAX_REDIRECTS,
-                timeout=30.0,
-                proxy=self.proxy,
-            ) as client:
-                r = await client.get(url, headers={"User-Agent": USER_AGENT})
-                r.raise_for_status()
+        try:
+            logger.debug("WebFetch: {}", "proxy enabled" if self.proxy else "direct connection")
+            client = self._http_factory.create()
+            r = await http_request("GET", url, client=client, headers={"User-Agent": USER_AGENT})
@@
-        except httpx.ProxyError as e:
-            logger.error("WebFetch proxy error for {}: {}", url, e)
-            return json.dumps({"error": f"Proxy error: {e}", "url": url}, ensure_ascii=False)
-        except Exception as e:
-            logger.error("WebFetch error for {}: {}", url, e)
-            return json.dumps({"error": str(e), "url": url}, ensure_ascii=False)
+        except httpx.ProxyError as e:
+            logger.error("WebFetch proxy error for {}: {}", url, e)
+            return json.dumps({"error": f"Proxy error: {e}", "url": url}, ensure_ascii=False)
+        except Exception as e:
+            logger.error("WebFetch error for {}: {}", url, e)
+            return json.dumps({"error": str(e), "url": url}, ensure_ascii=False)
