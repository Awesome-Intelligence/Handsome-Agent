#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gateway HTTP server - Hermes-style architecture."""

import json
import argparse
import time
import uuid
import psutil
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any
from .config import GatewayConfig
from .middleware import RateLimitMiddleware, AuthMiddleware


class HealthCheck:
    """Health check utilities."""

    @staticmethod
    def check_process() -> Dict[str, Any]:
        """Check if process is alive."""
        return {
            "status": "alive",
            "pid": os.getpid(),
            "uptime_seconds": round(time.time() - psutil.Process().create_time(), 2)
        }

    @staticmethod
    def check_dependencies() -> Dict[str, Any]:
        """Check if dependencies are available."""
        checks = {
            "python": True,
            "memory_available": psutil.virtual_memory().available > 100 * 1024 * 1024,
            "agent_loaded": _agent is not None,
            "llm_provider_loaded": _llm_provider is not None
        }
        all_healthy = all(checks.values())
        return {
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks
        }

    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """Get system statistics."""
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": round(mem.percent, 2),
            "memory_available_mb": mem.available // (1024 * 1024)
        }


# Global instances for Hermes-style architecture
_agent = None
_llm_provider = None
_acp_adapter = None


def init_agent(agent, llm_provider=None):
    """Initialize the agent and provider for Gateway use."""
    global _agent, _llm_provider, _acp_adapter
    
    _agent = agent
    _llm_provider = llm_provider
    
    if agent is not None:
        from agent.acp_adapter import ACPAdapter
        _acp_adapter = ACPAdapter(agent)


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler - Entry Point for AIAgent."""

    rate_limiter: Optional[RateLimitMiddleware] = None
    auth_middleware: Optional[AuthMiddleware] = None
    config: Optional[GatewayConfig] = None
    start_time: float = time.time()

    def log_message(self, format, *args):
        """Suppress logging."""
        pass

    def send_json(self, status: int, data: dict):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')

        if self.config and self.config.enable_cors:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key')

        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_json(200, {"status": "ok"})

    def do_GET(self):
        """Handle GET requests - Hermes-style endpoints."""
        if self.path == '/health' or self.path == '/health/live':
            self._handle_health_live()
        elif self.path == '/health/ready':
            self._handle_health_ready()
        elif self.path == '/health':
            self._handle_health()
        elif self.path == '/stats':
            self._handle_stats()
        elif self.path == '/info':
            self._handle_info()
        elif self.path == '/routes':
            self._handle_routes()
        else:
            self.send_json(404, {"error": "Not found", "path": self.path})

    def do_POST(self):
        """Handle POST requests - Hermes-style ACP protocol."""
        if self.path == '/acp':
            self._handle_acp()
        elif self.path == '/respond':
            self._handle_respond()
        elif self.path.startswith('/v1/'):
            self._handle_v1_api()
        else:
            self.send_json(404, {"error": "Not found", "path": self.path})

    def _handle_health_live(self):
        """Liveness probe - is the process alive?"""
        health = HealthCheck.check_process()
        self.send_json(200, health)

    def _handle_health_ready(self):
        """Readiness probe - are dependencies ready?"""
        health = HealthCheck.check_dependencies()
        status_code = 200 if health["status"] == "ready" else 503
        self.send_json(status_code, health)

    def _handle_health(self):
        """Full health check with system status."""
        process_health = HealthCheck.check_process()
        deps_health = HealthCheck.check_dependencies()
        system_stats = HealthCheck.get_system_stats()

        overall_status = "healthy"
        if deps_health["status"] != "ready":
            overall_status = "degraded"
        if process_health["status"] != "alive":
            overall_status = "unhealthy"

        self.send_json(200, {
            "status": overall_status,
            "gateway": "HandsomeAgent Gateway v1.0",
            "uptime_seconds": round(time.time() - self.start_time, 2),
            "process": process_health,
            "dependencies": deps_health,
            "system": system_stats
        })

    def _handle_stats(self):
        """Enhanced statistics endpoint."""
        rate_stats = self.rate_limiter.get_stats() if self.rate_limiter else {}
        system_stats = HealthCheck.get_system_stats()

        stats = {
            "gateway": {
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "version": "1.0.0",
                "name": "HandsomeAgent Gateway"
            },
            "rate_limiting": rate_stats,
            "system": system_stats
        }

        if _agent:
            stats["agent"] = _agent.get_stats() if hasattr(_agent, 'get_stats') else {}

        self.send_json(200, stats)

    def _handle_info(self):
        """Gateway information endpoint."""
        self.send_json(200, {
            "name": "HandsomeAgent Gateway",
            "version": "1.0.0",
            "architecture": "Hermes-style",
            "endpoints": {
                "health": ["/health", "/health/live", "/health/ready"],
                "stats": ["/stats"],
                "acp": ["/acp"],
                "v1": ["/v1/*"],
                "legacy": ["/respond"]
            },
            "capabilities": {
                "auth": self.config.enable_auth if self.config else False,
                "rate_limit": self.config.enable_rate_limit if self.config else False,
                "cors": self.config.enable_cors if self.config else False
            }
        })

    def _handle_routes(self):
        """List registered routes."""
        routes = [
            {"path": "/acp", "method": "POST", "description": "ACP protocol endpoint"},
            {"path": "/respond", "method": "POST", "description": "Legacy respond endpoint"},
            {"path": "/health", "method": "GET", "description": "Full health check"},
            {"path": "/health/live", "method": "GET", "description": "Liveness probe"},
            {"path": "/health/ready", "method": "GET", "description": "Readiness probe"},
            {"path": "/stats", "method": "GET", "description": "Statistics"},
            {"path": "/info", "method": "GET", "description": "Gateway info"}
        ]
        self.send_json(200, {"routes": routes})

    def _handle_acp(self):
        """Handle ACP (Agent Communication Protocol) requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            acp_message = json.loads(body.decode())
            
            message_id = acp_message.get('message_id', str(uuid.uuid4()))
            action = acp_message.get('action', '')
            payload = acp_message.get('payload', {})
            sender = acp_message.get('sender', 'gateway')
            
            if action == 'respond':
                return self._handle_acp_respond(message_id, payload)
            elif action == 'register_tool':
                return self._handle_acp_register_tool(message_id, payload)
            elif action == 'register_provider':
                return self._handle_acp_register_provider(message_id, payload)
            elif action == 'get_stats':
                return self._handle_acp_get_stats(message_id)
            elif action == 'list_tools':
                return self._handle_acp_list_tools(message_id)
            elif action == 'health_check':
                return self._handle_acp_health(message_id)
            else:
                self.send_json(200, {
                    "version": "1.0",
                    "message_id": message_id,
                    "status": "error",
                    "error": f"Unknown action: {action}"
                })
                
        except Exception as e:
            self.send_json(200, {
                "version": "1.0",
                "message_id": str(uuid.uuid4()),
                "status": "error",
                "error": str(e)
            })

    def _handle_acp_respond(self, message_id: str, payload: dict):
        """Handle ACP respond action."""
        if not _agent:
            self.send_json(200, {
                "version": "1.0", "message_id": message_id,
                "status": "error", "error": "Agent not initialized"
            })
            return

        query = payload.get('query', '')
        context = payload.get('context', {})

        import asyncio
        try:
            response = asyncio.run(_agent.respond(query, context))
            self.send_json(200, {
                "version": "1.0",
                "message_id": message_id,
                "status": "success",
                "payload": {
                    "content": response.content,
                    "confidence": response.confidence,
                    "execution_time": response.execution_time,
                    "reasoning_steps": response.reasoning_steps,
                    "tool_calls": response.tool_calls if hasattr(response, 'tool_calls') else []
                }
            })
        except Exception as e:
            self.send_json(200, {
                "version": "1.0",
                "message_id": message_id,
                "status": "error",
                "error": str(e)
            })

    def _handle_acp_register_tool(self, message_id: str, payload: dict):
        """Handle ACP register_tool action."""
        self.send_json(200, {
            "version": "1.0",
            "message_id": message_id,
            "status": "success",
            "payload": {"message": "Tool registration via ACP not yet implemented"}
        })

    def _handle_acp_register_provider(self, message_id: str, payload: dict):
        """Handle ACP register_provider action."""
        self.send_json(200, {
            "version": "1.0",
            "message_id": message_id,
            "status": "success",
            "payload": {"message": "Provider registration via ACP not yet implemented"}
        })

    def _handle_acp_get_stats(self, message_id: str):
        """Handle ACP get_stats action."""
        stats = {"gateway": {"version": "1.0.0"}}
        if _agent and hasattr(_agent, 'get_stats'):
            stats["agent"] = _agent.get_stats()
        self.send_json(200, {
            "version": "1.0",
            "message_id": message_id,
            "status": "success",
            "payload": stats
        })

    def _handle_acp_list_tools(self, message_id: str):
        """Handle ACP list_tools action."""
        tools = []
        if _agent and hasattr(_agent, 'tool_dispatcher'):
            tools = list(_agent.tool_dispatcher.tools.keys())
        self.send_json(200, {
            "version": "1.0",
            "message_id": message_id,
            "status": "success",
            "payload": {"tools": tools}
        })

    def _handle_acp_health(self, message_id: str):
        """Handle ACP health_check action."""
        process_health = HealthCheck.check_process()
        deps_health = HealthCheck.check_dependencies()
        self.send_json(200, {
            "version": "1.0",
            "message_id": message_id,
            "status": "success",
            "payload": {
                "status": "healthy" if deps_health["status"] == "ready" else "degraded",
                "process": process_health,
                "dependencies": deps_health
            }
        })

    def _handle_respond(self):
        """Handle legacy respond endpoint."""
        api_key = self.headers.get('X-API-Key', '')
        client_ip = self.client_address[0] if self.client_address else "unknown"

        if self.auth_middleware and not self.auth_middleware.check(api_key):
            self.send_json(401, {
                "error": "Unauthorized",
                "message": "Invalid or missing API key"
            })
            return

        if self.rate_limiter and not self.rate_limiter.check(client_ip):
            self.send_json(429, {
                "error": "Rate limit exceeded",
                "message": f"Max {self.config.rate_limit} req/{self.config.rate_window}s"
            })
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode())

            import asyncio
            
            if _agent:
                response = asyncio.run(_agent.respond(data.get('query', '')))
                self.send_json(200, {
                    "content": response.content,
                    "confidence": response.confidence,
                    "execution_time": response.execution_time
                })
            else:
                self.send_json(200, {
                    "content": "Agent not initialized. Use /acp endpoint with AIAgent.",
                    "confidence": 0.0
                })

        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def _handle_v1_api(self):
        """Handle v1 API endpoints."""
        path = self.path.replace('/v1/', '')
        self.send_json(200, {
            "v1_api": True,
            "path": path,
            "message": "V1 API endpoints coming soon"
        })


def run_gateway(config: Optional[GatewayConfig] = None, agent=None, llm_provider=None):
    """Run the gateway server with Hermes-style architecture."""
    if config is None:
        config = GatewayConfig()
    
    GatewayHandler.config = config
    GatewayHandler.rate_limiter = RateLimitMiddleware(config)
    GatewayHandler.auth_middleware = AuthMiddleware(config)
    
    init_agent(agent, llm_provider)
    
    server = HTTPServer((config.host, config.port), GatewayHandler)
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                  HandsomeAgent Gateway                       ║
║                  Hermes-style Architecture                 ║
╠══════════════════════════════════════════════════════════════════╣
║  URL: http://{config.host}:{config.port}                          
║  Auth: {'Enabled' if config.enable_auth else 'Disabled'}                                       
║  Rate: {config.limit} req/{config.rate_window}s                              
╠══════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                  
║    ACP Protocol:                                           
║      POST /acp              - ACP protocol endpoint         
║                                                            
║    Health:                                                
║      GET  /health          - Full health check              
║      GET  /health/live     - Liveness probe               
║      GET  /health/ready    - Readiness probe              
║                                                            
║    Info:                                                  
║      GET  /stats           - Statistics                   
║      GET  /info            - Gateway info                
║      GET  /routes          - List routes                 
║                                                            
║    Legacy:                                                
║      POST /respond         - Legacy respond endpoint       
║                                                            
║  ACP Actions:                                            
║    respond, register_tool, register_provider             
║    get_stats, list_tools, health_check                   
╠══════════════════════════════════════════════════════════════════╣
║  Examples:                                                
║    curl http://{config.host}:{config.port}/health                   
║    curl -X POST http://{config.host}:{config.port}/acp \\          
║      -H "Content-Type: application/json" \\               
║      -d '{{"action":"respond","payload":{{"query":"hi"}}}}' 
╚══════════════════════════════════════════════════════════════════╝
🛑 Press Ctrl+C to stop...
""")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HandsomeAgent Gateway')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--rate-limit', type=int, default=100)
    parser.add_argument('--rate-window', type=int, default=60)
    parser.add_argument('--no-auth', action='store_true')
    parser.add_argument('--no-rate-limit', action='store_true')
    
    args = parser.parse_args()
    
    config = GatewayConfig(
        host=args.host,
        port=args.port,
        api_keys=[args.api_key] if args.api_key else [],
        rate_limit=args.rate_limit,
        rate_window=args.rate_window,
        enable_auth=not args.no_auth,
        enable_rate_limit=not args.no_rate_limit
    )
    
    run_gateway(config)
