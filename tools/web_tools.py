#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web search and extraction tools for the agent.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, List
from . import ToolResult, register_tool


@register_tool(
    name="web_search",
    description="网络搜索",
    parameters=[
        {"name": "query", "type": "string", "required": True, "description": "搜索关键词"},
        {"name": "limit", "type": "integer", "required": False, "description": "结果数量"}
    ]
)
def web_search(query: str, limit: int = 5) -> ToolResult:
    """网络搜索"""
    try:
        from core.config import settings
        
        api_key = getattr(settings, 'TAVILY_API_KEY', None) or getattr(settings, 'SEARCH_API_KEY', None)
        
        if api_key:
            return tavily_search(query, limit, api_key)
        
        return duckduckgo_search(query, limit)
        
    except Exception as e:
        return fallback_search(query, limit)


def tavily_search(query: str, limit: int, api_key: str) -> ToolResult:
    """使用Tavily API搜索"""
    try:
        url = "https://api.tavily.com/search"
        data = json.dumps({"query": query, "max_results": limit}).encode()
        
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
        
        if "results" in result:
            output = f"找到 {len(result['results'])} 个结果:\n\n"
            for i, r in enumerate(result['results'][:limit], 1):
                output += f"{i}. {r.get('title', '无标题')}\n"
                output += f"   {r.get('url', '')}\n"
                output += f"   {r.get('content', '')[:200]}...\n\n"
            
            return ToolResult(success=True, output=output, data={"results": result['results']})
        
        return ToolResult(success=False, output="", error="搜索API返回格式错误")
        
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Tavily搜索失败: {str(e)}")


def duckduckgo_search(query: str, limit: int) -> ToolResult:
    """使用DuckDuckGo HTML搜索（无API Key时备用）"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        import re
        results = re.findall(r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>', html)
        snippets = re.findall(r'<a class="result__snippet" href="[^"]+">([^<]+)</a>', html)
        
        if not results:
            return fallback_search(query, limit)
        
        output = f"找到 {min(len(results), limit)} 个结果:\n\n"
        for i, ((url, title), *snippet) in enumerate(zip(results[:limit], snippets[:limit]), 1):
            output += f"{i}. {title}\n"
            output += f"   {url}\n"
            if snippet:
                clean_snippet = re.sub(r'<[^>]+>', '', snippet[0])
                output += f"   {clean_snippet[:150]}...\n"
            output += "\n"
        
        return ToolResult(success=True, output=output)
        
    except Exception as e:
        return fallback_search(query, limit)


def fallback_search(query: str, limit: int) -> ToolResult:
    """回退搜索：直接使用搜索引擎"""
    try:
        encoded_query = urllib.parse.quote(query)
        bing_url = f"https://www.bing.com/search?q={encoded_query}"
        
        output = f"建议手动访问以下链接搜索:\n\n"
        output += f"🔍 Bing: {bing_url}\n"
        output += f"🔍 Google: https://www.google.com/search?q={encoded_query}\n"
        output += f"🔍 DuckDuckGo: https://duckduckgo.com/?q={encoded_query}\n"
        
        return ToolResult(success=True, output=output)
    except Exception as e:
        return ToolResult(success=False, output="", error=f"搜索失败: {str(e)}")


@register_tool(
    name="web_extract",
    description="提取网页内容",
    parameters=[
        {"name": "urls", "type": "array", "required": True, "description": "URL列表"},
        {"name": "limit", "type": "integer", "required": False, "description": "每个页面字符数限制"}
    ]
)
def web_extract(urls: List[str], limit: int = 2000) -> ToolResult:
    """提取网页内容"""
    try:
        import re
        
        results = []
        for url in urls[:5]:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                
                text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                
                if len(text) > limit:
                    text = text[:limit] + "..."
                
                results.append({
                    "url": url,
                    "content": text,
                    "length": len(text)
                })
                
            except Exception as e:
                results.append({
                    "url": url,
                    "error": str(e)
                })
        
        output = f"提取了 {len(results)} 个页面:\n\n"
        for r in results:
            if "error" in r:
                output += f"❌ {r['url']}: {r['error']}\n\n"
            else:
                output += f"✅ {r['url']} ({r['length']} 字符)\n"
                output += f"内容预览: {r['content'][:300]}...\n\n"
        
        return ToolResult(success=True, output=output, data={"results": results})
        
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="fetch_url",
    description="获取URL内容",
    parameters=[
        {"name": "url", "type": "string", "required": True, "description": "URL地址"}
    ]
)
def fetch_url(url: str) -> ToolResult:
    """获取URL内容"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get('Content-Type', '')
            
            if 'text/html' in content_type:
                html = response.read().decode('utf-8', errors='ignore')
                import re
                text = re.sub(r'<[^>]+>', ' ', html)
                text = re.sub(r'\s+', ' ', text).strip()
                return ToolResult(success=True, output=text[:5000])
            else:
                return ToolResult(success=True, output=f"[二进制内容，长度: {response.headers.get('Content-Length', '未知')}]")
                
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))
