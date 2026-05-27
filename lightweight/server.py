#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight HTTP server for mobile backend deployment
"""

import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from .agent import LightweightAgent, get_agent


class AgentAPIHandler(BaseHTTPRequestHandler):
    """REST API handler."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/respond':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body.decode())
                
                agent = get_agent()
                response = asyncio.run(agent.respond(data.get('query', '')))
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "content": response.content,
                    "confidence": response.confidence,
                    "execution_time": response.execution_time
                }).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()


def run_server(host: str = 'localhost', port: int = 8000):
    """Run the agent API server."""
    server = HTTPServer((host, port), AgentAPIHandler)
    print(f"🚀 Lightweight Agent Server")
    print(f"   URL: http://{host}:{port}")
    print(f"   Health: GET /health")
    print(f"   Query: POST /respond")
    print(f"\n🛑 Press Ctrl+C to stop...\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.shutdown()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        run_server()
    else:
        print("⚡ Lightweight Agent - Interactive Mode")
        print("=" * 50)
        
        agent = LightweightAgent()
        
        while True:
            try:
                query = input("\n❓ You: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                if not query:
                    continue
                
                response = asyncio.run(agent.respond(query))
                
                print(f"\n✅ Agent: {response.content}")
                print(f"   [Confidence: {response.confidence:.1f}, Time: {response.execution_time:.3f}s]")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n👋 Goodbye!")
