#!/usr/bin/env python3
"""
LainNet Tracer - Claude Agent SDK Traffic Logger
Intercepts SDK subprocess communication and logs to claude-trace compatible JSONL format
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import threading
import subprocess


class LainTracer:
    """Traffic logger for Claude Agent SDK subprocess communication"""

    def __init__(self, layer: str = "unknown"):
        self.layer = layer
        self.log_dir = Path("/app/.lain-trace")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.jsonl_file = self.log_dir / f"{layer}-{timestamp}.jsonl"
        self.html_file = self.log_dir / f"{layer}-{timestamp}.html"

        # Request tracking
        self.pending_requests: Dict[str, Dict] = {}
        self.request_counter = 0
        self.lock = threading.Lock()

        print(f"[LainTracer] Initialized for layer: {layer}")
        print(f"[LainTracer] JSONL: {self.jsonl_file}")
        print(f"[LainTracer] HTML:  {self.html_file}")

    def generate_request_id(self) -> str:
        """Generate unique request ID"""
        with self.lock:
            self.request_counter += 1
            return f"req_{int(time.time())}_{self.request_counter}"

    def log_request(self, request_data: Dict[str, Any]) -> str:
        """Log an API request and return request ID"""
        request_id = self.generate_request_id()

        # Extract relevant data
        messages = request_data.get("messages", [])
        model = request_data.get("model", "unknown")
        system = request_data.get("system")

        # Create request record
        request_record = {
            "timestamp": time.time(),
            "method": "POST",
            "url": "https://api.anthropic.com/v1/messages",
            "headers": {
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            "body": request_data
        }

        # Store pending request
        with self.lock:
            self.pending_requests[request_id] = request_record

        return request_id

    def log_response(self, request_id: str, response_data: Any, is_streaming: bool = False):
        """Log API response and write to JSONL"""
        with self.lock:
            if request_id not in self.pending_requests:
                print(f"[LainTracer] Warning: No matching request for {request_id}")
                return

            request_record = self.pending_requests.pop(request_id)

        # Create response record
        if is_streaming:
            # For streaming responses, response_data should be the raw SSE text
            response_record = {
                "timestamp": time.time(),
                "status_code": 200,
                "headers": {
                    "content-type": "text/event-stream"
                },
                "body_raw": response_data if isinstance(response_data, str) else ""
            }
        else:
            # For non-streaming, response_data is a Message object
            response_record = {
                "timestamp": time.time(),
                "status_code": 200,
                "headers": {
                    "content-type": "application/json"
                },
                "body": response_data
            }

        # Create RawPair
        pair = {
            "request": request_record,
            "response": response_record,
            "logged_at": datetime.now().isoformat()
        }

        # Write to JSONL file
        try:
            with open(self.jsonl_file, "a") as f:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[LainTracer] Error writing to JSONL: {e}")

    def generate_html(self):
        """Generate HTML report using claude-trace CLI"""
        try:
            cmd = [
                "claude-trace",
                "--generate-html",
                str(self.jsonl_file),
                str(self.html_file)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[LainTracer] HTML generated: {self.html_file}")
        except subprocess.CalledProcessError as e:
            print(f"[LainTracer] HTML generation failed: {e.stderr.decode()}")
        except FileNotFoundError:
            print("[LainTracer] claude-trace not found, skipping HTML generation")

    def cleanup(self):
        """Cleanup and generate final HTML report"""
        print(f"[LainTracer] Cleanup - logged {self.request_counter} requests")
        self.generate_html()


# Global tracer instance
_tracer: Optional[LainTracer] = None


def init_tracer(layer: str = "unknown"):
    """Initialize global tracer instance"""
    global _tracer

    if _tracer is not None:
        print(f"[LainTracer] Already initialized for layer: {_tracer.layer}")
        return _tracer

    _tracer = LainTracer(layer=layer)

    # Apply monkey patches
    apply_sdk_patches()

    return _tracer


def get_tracer() -> Optional[LainTracer]:
    """Get global tracer instance"""
    return _tracer


def apply_sdk_patches():
    """Apply monkey patches to ClaudeSDKClient for traffic logging"""
    try:
        from claude_agent_sdk import ClaudeSDKClient

        # Save original methods
        _original_query = ClaudeSDKClient.query
        _original_receive_response = ClaudeSDKClient.receive_response

        # Patch query method to capture requests
        async def patched_query(self, prompt, session_id=None):
            """Patched query method that logs requests"""
            tracer = get_tracer()

            # Log request if tracer is enabled
            if tracer:
                try:
                    # Build request data - use correct default model
                    request_data = {
                        "model": "claude-sonnet-4-5",
                        "messages": [{"role": "user", "content": prompt}]
                    }

                    # Try to get system prompt from options
                    if hasattr(self, '_options'):
                        options = self._options
                        if hasattr(options, "model") and options.model:
                            request_data["model"] = options.model
                        if hasattr(options, "system_prompt") and options.system_prompt:
                            request_data["system"] = options.system_prompt

                    # Add session_id if present
                    if session_id:
                        request_data["session_id"] = session_id

                    request_id = tracer.log_request(request_data)
                    # Store request_id in client instance for later use
                    self._lain_request_id = request_id
                except Exception as e:
                    print(f"[LainTracer] Error logging request: {e}")

            # Call original method
            result = await _original_query(self, prompt, session_id)
            return result

        # Patch receive_response to capture streaming responses
        async def patched_receive_response(self):
            """Patched receive_response that logs responses"""
            tracer = get_tracer()
            request_id = getattr(self, '_lain_request_id', None)

            # Collect streaming response
            response_events = []

            try:
                async for message in _original_receive_response(self):
                    # Collect events for logging
                    if tracer:
                        try:
                            # Get message type name from class
                            msg_type = type(message).__name__

                            event_data = {
                                "type": msg_type,
                            }

                            # Add content if available
                            if hasattr(message, 'content'):
                                try:
                                    content = message.content
                                    if isinstance(content, list):
                                        # Format content blocks with proper types
                                        event_data["content"] = [
                                            {
                                                "type": type(block).__name__,
                                                "text": getattr(block, "text", "")
                                            }
                                            for block in content
                                        ]
                                    else:
                                        event_data["content"] = str(content)
                                except Exception as e:
                                    event_data["content"] = f"<<error: {e}>>"

                            response_events.append(event_data)
                        except Exception as e:
                            print(f"[LainTracer] Error collecting event: {e}")

                    # Yield message to caller
                    yield message

                # Log complete response after stream finishes
                if tracer and request_id and response_events:
                    try:
                        # Convert events to SSE format
                        sse_text = "\n".join([
                            f"data: {json.dumps(event, ensure_ascii=False)}"
                            for event in response_events
                        ])
                        tracer.log_response(request_id, sse_text, is_streaming=True)
                    except Exception as e:
                        print(f"[LainTracer] Error logging response: {e}")

            except Exception as e:
                print(f"[LainTracer] Error during streaming: {e}")
                raise

        # Apply patches to ClaudeSDKClient class
        ClaudeSDKClient.query = patched_query
        ClaudeSDKClient.receive_response = patched_receive_response

        print("[LainTracer] ClaudeSDKClient patches applied successfully")

    except ImportError as e:
        print(f"[LainTracer] Failed to patch SDK: {e}")
    except Exception as e:
        print(f"[LainTracer] Unexpected error applying patches: {e}")


# Auto-initialize if environment variable is set
if os.getenv("LAIN_TRACE_ENABLED") == "1":
    layer = os.getenv("LAIN_TRACE_LAYER", "unknown")
    init_tracer(layer=layer)

    # Register cleanup on exit
    import atexit
    atexit.register(lambda: get_tracer().cleanup() if get_tracer() else None)
