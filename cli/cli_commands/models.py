#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model catalog for Handsome Agent CLI.

🚪 Access - 💬 CLI - 模型目录

提供模型信息、对比、推荐功能。
"""

from typing import Dict, List, Optional, Any


# 模型定义
MODELS: Dict[str, Dict[str, Any]] = {
    # OpenAI
    "gpt-4o": {
        "provider": "openai",
        "name": "GPT-4o",
        "context_window": 128000,
        "input_price": 5.0,
        "output_price": 15.0,
        "capabilities": ["chat", "vision", "function_calling", "json_mode"],
        "description": "Most capable model, supports vision and function calling",
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "name": "GPT-4o Mini",
        "context_window": 128000,
        "input_price": 0.15,
        "output_price": 0.6,
        "capabilities": ["chat", "vision", "function_calling"],
        "description": "Faster, cheaper version of GPT-4o",
    },
    "gpt-4-turbo": {
        "provider": "openai",
        "name": "GPT-4 Turbo",
        "context_window": 128000,
        "input_price": 10.0,
        "output_price": 30.0,
        "capabilities": ["chat", "vision", "function_calling"],
        "description": "Previous generation flagship model",
    },
    "gpt-3.5-turbo": {
        "provider": "openai",
        "name": "GPT-3.5 Turbo",
        "context_window": 16385,
        "input_price": 0.5,
        "output_price": 1.5,
        "capabilities": ["chat", "function_calling"],
        "description": "Fast and affordable model",
    },
    # Anthropic
    "claude-3-5-sonnet-20241022": {
        "provider": "anthropic",
        "name": "Claude 3.5 Sonnet",
        "context_window": 200000,
        "input_price": 3.0,
        "output_price": 15.0,
        "capabilities": ["chat", "vision", "function_calling", "long_context"],
        "description": "Latest Claude model, excellent at coding",
    },
    "claude-3-opus-20240229": {
        "provider": "anthropic",
        "name": "Claude 3 Opus",
        "context_window": 200000,
        "input_price": 15.0,
        "output_price": 75.0,
        "capabilities": ["chat", "vision", "function_calling", "long_context"],
        "description": "Most capable Claude model",
    },
    # Google
    "gemini-1.5-flash": {
        "provider": "google",
        "name": "Gemini 1.5 Flash",
        "context_window": 1000000,
        "input_price": 0.075,
        "output_price": 0.3,
        "capabilities": ["chat", "vision", "function_calling", "long_context"],
        "description": "Fast with 1M context window",
    },
    "gemini-1.5-pro": {
        "provider": "google",
        "name": "Gemini 1.5 Pro",
        "context_window": 1000000,
        "input_price": 1.25,
        "output_price": 5.0,
        "capabilities": ["chat", "vision", "function_calling", "long_context"],
        "description": "Most capable Gemini model",
    },
    # DeepSeek
    "deepseek-chat": {
        "provider": "deepseek",
        "name": "DeepSeek Chat",
        "context_window": 64000,
        "input_price": 0.14,
        "output_price": 0.28,
        "capabilities": ["chat", "function_calling", "coding"],
        "description": "Affordable, great for coding",
    },
    "deepseek-coder": {
        "provider": "deepseek",
        "name": "DeepSeek Coder",
        "context_window": 64000,
        "input_price": 0.14,
        "output_price": 0.28,
        "capabilities": ["chat", "coding"],
        "description": "Specialized for code generation",
    },
    # MiniMax
    "MiniMax-Text-01": {
        "provider": "minimax",
        "name": "MiniMax Text 01",
        "context_window": 1000000,
        "input_price": 0.1,
        "output_price": 0.1,
        "capabilities": ["chat", "function_calling", "long_context"],
        "description": "1M context window, affordable",
    },
    # Moonshot
    "moonshot-v1-8k": {
        "provider": "moonshot",
        "name": "Moonshot V1 8K",
        "context_window": 8000,
        "input_price": 0.06,
        "output_price": 0.06,
        "capabilities": ["chat"],
        "description": "Fast and affordable",
    },
    "moonshot-v1-32k": {
        "provider": "moonshot",
        "name": "Moonshot V1 32K",
        "context_window": 32000,
        "input_price": 0.06,
        "output_price": 0.06,
        "capabilities": ["chat", "long_context"],
        "description": "32K context window",
    },
    "moonshot-v1-128k": {
        "provider": "moonshot",
        "name": "Moonshot V1 128K",
        "context_window": 128000,
        "input_price": 0.06,
        "output_price": 0.06,
        "capabilities": ["chat", "long_context"],
        "description": "128K context window",
    },
    # Groq
    "llama-3.1-8b-instant": {
        "provider": "groq",
        "name": "Llama 3.1 8B Instant",
        "context_window": 128000,
        "input_price": 0.0,
        "output_price": 0.0,
        "capabilities": ["chat", "fast_inference"],
        "description": "Free tier, very fast inference",
    },
    "llama-3.1-70b-versatile": {
        "provider": "groq",
        "name": "Llama 3.1 70B Versatile",
        "context_window": 128000,
        "input_price": 0.59,
        "output_price": 0.79,
        "capabilities": ["chat", "function_calling"],
        "description": "Most capable Groq model",
    },
    # Zhipu
    "glm-4-flash": {
        "provider": "zhipu",
        "name": "GLM-4 Flash",
        "context_window": 128000,
        "input_price": 0.1,
        "output_price": 0.1,
        "capabilities": ["chat", "function_calling"],
        "description": "Fast and affordable",
    },
    "glm-4": {
        "provider": "zhipu",
        "name": "GLM-4",
        "context_window": 128000,
        "input_price": 1.0,
        "output_price": 1.0,
        "capabilities": ["chat", "function_calling", "vision"],
        "description": "Most capable Zhipu model",
    },
    # DashScope
    "qwen-turbo": {
        "provider": "dashscope",
        "name": "Qwen Turbo",
        "context_window": 8000,
        "input_price": 0.02,
        "output_price": 0.06,
        "capabilities": ["chat", "vision", "function_calling"],
        "description": "Fast and affordable Alibaba model",
    },
    "qwen-plus": {
        "provider": "dashscope",
        "name": "Qwen Plus",
        "context_window": 32000,
        "input_price": 0.04,
        "output_price": 0.12,
        "capabilities": ["chat", "vision", "function_calling"],
        "description": "Balanced performance and price",
    },
    # VolcEngine
    "doubao-pro-32k": {
        "provider": "volcengine",
        "name": "Doubao Pro 32K",
        "context_window": 32000,
        "input_price": 0.05,
        "output_price": 0.05,
        "capabilities": ["chat", "function_calling"],
        "description": "ByteDance's LLM",
    },
}


def list_models(provider: Optional[str] = None, json_output: bool = False) -> None:
    """List all available models.
    
    Args:
        provider: Filter by provider
        json_output: Output as JSON
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header
    
    print_header("🤖 模型目录")
    
    models_list = []
    for model_id, model in MODELS.items():
        if provider and model.get("provider") != provider:
            continue
        
        models_list.append({
            "id": model_id,
            "name": model["name"],
            "provider": model.get("provider", ""),
            "context_window": model.get("context_window", 0),
            "input_price": model.get("input_price", 0),
            "output_price": model.get("output_price", 0),
        })
    
    if json_output:
        import json
        print(json.dumps({"models": models_list}, indent=2, ensure_ascii=False))
        return
    
    print()
    print(color("  Model", Colors.BOLD), end="")
    print(color(" " * 30, Colors.DIM), end="")
    print(color("Provider", Colors.DIM), end="")
    print(color(" " * 12, Colors.DIM), end="")
    print(color("Context", Colors.DIM), end="")
    print(color(" " * 10, Colors.DIM), end="")
    print(color("Price I/O", Colors.DIM))
    print(color("-" * 110, Colors.DIM))
    
    for m in sorted(models_list, key=lambda x: x["input_price"]):
        name = m["name"][:30] if len(m["name"]) > 30 else m["name"]
        provider_name = m["provider"][:12] if len(m["provider"]) > 12 else m["provider"]
        
        context = m["context_window"]
        if context >= 1000000:
            context_str = f"{context // 1000000}M"
        elif context >= 1000:
            context_str = f"{context // 1000}K"
        else:
            context_str = str(context)
        
        price = f"${m['input_price']:.2f}/${m['output_price']:.2f}"
        
        print(f"  {color(name, Colors.AVOCADO_BRIGHT):30s} {provider_name:12s} {context_str:>8s} {price}")
    
    print()
    print(color(f"  Total: {len(models_list)} models", Colors.DIM))


def get_model_info(model_id: str) -> None:
    """Show detailed information about a model.
    
    Args:
        model_id: Model ID
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_error
    
    print_header(f"🤖 Model: {model_id}")
    
    if model_id not in MODELS:
        print_error(f"Model not found: {model_id}")
        # 尝试模糊搜索
        similar = [m for m in MODELS.keys() if model_id.lower() in m.lower()]
        if similar:
            print()
            print(f"Similar models: {', '.join(similar[:5])}")
        return
    
    model = MODELS[model_id]
    
    print()
    print(color(f"  Name: ", Colors.DIM) + color(model["name"], Colors.WHITE))
    print(color(f"  Provider: ", Colors.DIM) + color(model.get("provider", "N/A"), Colors.WHITE))
    print(color(f"  Description: ", Colors.DIM) + color(model.get("description", "N/A"), Colors.WHITE))
    print()
    
    context = model.get("context_window", 0)
    if context >= 1000000:
        context_str = f"{context / 1000000}M tokens"
    elif context >= 1000:
        context_str = f"{context / 1000}K tokens"
    else:
        context_str = f"{context} tokens"
    
    print(color(f"  Context Window: ", Colors.DIM) + color(context_str, Colors.WHITE))
    
    print(color(f"  Pricing ($/1M tokens):", Colors.AVOCADO_BRIGHT))
    print(f"    Input: ${model.get('input_price', 0):.2f}")
    print(f"    Output: ${model.get('output_price', 0):.2f}")
    
    print()
    print(color(f"  Capabilities:", Colors.AVOCADO_BRIGHT))
    for cap in model.get("capabilities", []):
        print(f"    • {cap}")


def compare_models(model1_id: str, model2_id: str) -> None:
    """Compare two models side by side.
    
    Args:
        model1_id: First model ID
        model2_id: Second model ID
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_error
    
    print_header(f"📊 模型对比: {model1_id} vs {model2_id}")
    
    if model1_id not in MODELS:
        print_error(f"Model not found: {model1_id}")
        return
    if model2_id not in MODELS:
        print_error(f"Model not found: {model2_id}")
        return
    
    m1 = MODELS[model1_id]
    m2 = MODELS[model2_id]
    
    print()
    print(color("  Property", Colors.DIM), end="")
    print(color(f" {' ' * 20}{model1_id[:20]:20s}", Colors.AVOCADO_BRIGHT), end="")
    print(color(f" {' ' * 20}{model2_id[:20]:20s}", Colors.AVOCADO_BRIGHT))
    print(color("-" * 100, Colors.DIM))
    
    # Provider
    print(f"  {color('Provider', Colors.DIM):15s} {m1.get('provider', 'N/A'):20s} {m2.get('provider', 'N/A'):20s}")
    
    # Context
    c1 = m1.get("context_window", 0)
    c2 = m2.get("context_window", 0)
    c1_str = f"{c1 // 1000}K" if c1 < 1000000 else f"{c1 // 1000000}M"
    c2_str = f"{c2 // 1000}K" if c2 < 1000000 else f"{c2 // 1000000}M"
    winner = "✓" if c1 > c2 else ("←" if c1 == c2 else "")
    print(f"  {color('Context', Colors.DIM):15s} {c1_str:20s} {c2_str:20s} {color(winner, Colors.GREEN)}")
    
    # Input Price
    p1 = m1.get("input_price", 0)
    p2 = m2.get("input_price", 0)
    winner = "✓" if p1 < p2 else ("=" if p1 == p2 else "")
    print(f"  {color('Input Price', Colors.DIM):15s} ${p1:.2f}/M{'':12s} ${p2:.2f}/M{'':12s} {color(winner, Colors.GREEN)}")
    
    # Output Price
    p1 = m1.get("output_price", 0)
    p2 = m2.get("output_price", 0)
    winner = "✓" if p1 < p2 else ("=" if p1 == p2 else "")
    print(f"  {color('Output Price', Colors.DIM):15s} ${p1:.2f}/M{'':12s} ${p2:.2f}/M{'':12s} {color(winner, Colors.GREEN)}")
    
    # Capabilities
    caps1 = set(m1.get("capabilities", []))
    caps2 = set(m2.get("capabilities", []))
    shared = caps1 & caps2
    print(f"  {color('Capabilities', Colors.DIM):15s}")
    print(f"    {model1_id[:20]}: {', '.join(caps1) if caps1 else 'N/A'}")
    print(f"    {model2_id[:20]}: {', '.join(caps2) if caps2 else 'N/A'}")
    print(f"    {color('Shared:', Colors.DIM)} {', '.join(shared)}")
    
    print()


def search_models(query: str) -> List[str]:
    """Search models by name or capability.
    
    Args:
        query: Search query
        
    Returns:
        List of matching model IDs
    """
    results = []
    query_lower = query.lower()
    
    for model_id, model in MODELS.items():
        if query_lower in model_id.lower():
            results.append(model_id)
        elif query_lower in model.get("name", "").lower():
            results.append(model_id)
        elif query_lower in model.get("description", "").lower():
            results.append(model_id)
        elif any(query_lower in cap.lower() for cap in model.get("capabilities", [])):
            results.append(model_id)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Model catalog")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    list_parser = subparsers.add_parser("list", help="List all models")
    list_parser.add_argument("--provider", help="Filter by provider")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    info_parser = subparsers.add_parser("info", help="Show model info")
    info_parser.add_argument("model_id", help="Model ID")
    
    compare_parser = subparsers.add_parser("compare", help="Compare two models")
    compare_parser.add_argument("model1", help="First model ID")
    compare_parser.add_argument("model2", help="Second model ID")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_models(provider=args.provider, json_output=args.json)
    elif args.command == "info":
        get_model_info(args.model_id)
    elif args.command == "compare":
        compare_models(args.model1, args.model2)
    else:
        list_models()