"""
Sandbox server for the Seasonal Farm Market.
Hosts the game engine and executes tool calls via HTTP.
Pure stdlib only. No code execution or file access tools.
"""
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import os

# simcore is copied into the image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simcore.engine import Engine

MAX_REQUEST_BODY = 65536  # 64 KB cap
engine = None
engine_lock = threading.Lock()


class SandboxHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the sandbox."""

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_json(self, data, status=200):
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_REQUEST_BODY:
            return None, "Request body too large"
        if length == 0:
            return {}, None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw), None
        except (json.JSONDecodeError, ValueError) as e:
            return None, f"Invalid JSON: {e}"

    def do_POST(self):
        global engine
        path = self.path.rstrip("/")

        if path == "/reset":
            self._handle_reset()
        elif path == "/execute":
            self._handle_execute()
        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def do_GET(self):
        path = self.path.rstrip("/")
        if path == "/state":
            self._handle_state()
        elif path == "/health":
            self._send_json({"status": "ok"})
        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def _handle_reset(self):
        global engine
        body, err = self._read_body()
        if err:
            self._send_json({"error": err}, 400)
            return

        try:
            world = body.get("world")
            if not world:
                self._send_json({"error": "Missing 'world' in request body"}, 400)
                return

            with engine_lock:
                engine = Engine(world)
                h = engine.get_state_hash()

            self._send_json({"status": "ok", "state_hash": h})
        except Exception as e:
            self._send_json({"error": f"Reset failed: {e}"}, 500)

    def _handle_execute(self):
        global engine
        if engine is None:
            self._send_json({"error": "No game loaded. Call /reset first."}, 400)
            return

        body, err = self._read_body()
        if err:
            self._send_json({"error": err}, 400)
            return

        tool_name = body.get("tool")
        arguments = body.get("arguments", {})

        if not isinstance(tool_name, str):
            self._send_json({"error": "Missing or invalid 'tool' field."}, 400)
            return
        if not isinstance(arguments, dict):
            self._send_json({"error": "'arguments' must be a JSON object."}, 400)
            return

        # Validate tool exists
        valid_tools = [
            "get_status", "get_market", "get_forecast", "get_news",
            "plant", "harvest", "sell", "take_loan", "repay",
            "advance_days", "finish"
        ]
        if tool_name not in valid_tools:
            self._send_json({
                "result": f"Unknown tool '{tool_name}'. Valid tools: {', '.join(valid_tools)}",
                "is_error": True,
                "done": False,
                "state_hash": engine.get_state_hash() if engine else ""
            })
            return

        try:
            with engine_lock:
                result = self._execute_tool(tool_name, arguments)
            self._send_json(result)
        except Exception as e:
            self._send_json({
                "result": f"Internal error: {e}",
                "is_error": True,
                "done": False,
                "state_hash": engine.get_state_hash() if engine else ""
            }, 500)

    def _execute_tool(self, tool_name, arguments):
        """Execute a tool call with validation. Returns result dict."""
        global engine

        try:
            # Validate and convert arguments
            args = self._validate_args(tool_name, arguments)
            if isinstance(args, str):
                # Validation error
                return {
                    "result": args,
                    "is_error": True,
                    "done": False,
                    "state_hash": engine.get_state_hash()
                }

            # Execute
            method = getattr(engine, tool_name)
            text, is_error, done = method(**args)

            # Truncate output
            if len(text) > 4000:
                text = text[:4000] + "\n... (truncated)"

            return {
                "result": text,
                "is_error": is_error,
                "done": done,
                "state_hash": engine.get_state_hash()
            }
        except Exception as e:
            return {
                "result": f"Tool execution error: {e}",
                "is_error": True,
                "done": False,
                "state_hash": engine.get_state_hash()
            }

    def _validate_args(self, tool_name, arguments):
        """
        Validate and convert arguments. Returns cleaned args dict or error string.
        Defense in depth: the harness also validates, but the sandbox re-validates.
        """
        # Reject unexpected keys
        valid_keys = {
            "get_status": set(),
            "get_market": {"history_days"},
            "get_forecast": set(),
            "get_news": set(),
            "plant": {"plot_id", "crop"},
            "harvest": {"plot_id"},
            "sell": {"crop", "quantity"},
            "take_loan": {"amount_cents"},
            "repay": {"amount_cents"},
            "advance_days": {"n"},
            "finish": set(),
        }

        expected = valid_keys.get(tool_name, set())
        unexpected = set(arguments.keys()) - expected
        if unexpected:
            return f"Unexpected arguments: {', '.join(sorted(unexpected))}. Expected: {', '.join(sorted(expected)) or 'none'}"

        args = {}
        try:
            if tool_name == "get_market":
                if "history_days" in arguments:
                    args["history_days"] = self._to_int(arguments["history_days"], "history_days", 0, 7)
                    if isinstance(args["history_days"], str):
                        return args["history_days"]

            elif tool_name == "plant":
                if "plot_id" not in arguments or "crop" not in arguments:
                    return "Missing required arguments: plot_id, crop"
                args["plot_id"] = self._to_int(arguments["plot_id"], "plot_id", 0, 100)
                if isinstance(args["plot_id"], str):
                    return args["plot_id"]
                crop = arguments["crop"]
                if not isinstance(crop, str) or len(crop) > 50:
                    return "crop must be a string (max 50 chars)"
                args["crop"] = crop

            elif tool_name == "harvest":
                if "plot_id" not in arguments:
                    return "Missing required argument: plot_id"
                args["plot_id"] = self._to_int(arguments["plot_id"], "plot_id", 0, 100)
                if isinstance(args["plot_id"], str):
                    return args["plot_id"]

            elif tool_name == "sell":
                if "crop" not in arguments or "quantity" not in arguments:
                    return "Missing required arguments: crop, quantity"
                crop = arguments["crop"]
                if not isinstance(crop, str) or len(crop) > 50:
                    return "crop must be a string (max 50 chars)"
                args["crop"] = crop
                args["quantity"] = self._to_int(arguments["quantity"], "quantity", 1, 10000)
                if isinstance(args["quantity"], str):
                    return args["quantity"]

            elif tool_name == "take_loan":
                if "amount_cents" not in arguments:
                    return "Missing required argument: amount_cents"
                args["amount_cents"] = self._to_int(arguments["amount_cents"], "amount_cents", 1, 10000000)
                if isinstance(args["amount_cents"], str):
                    return args["amount_cents"]

            elif tool_name == "repay":
                if "amount_cents" not in arguments:
                    return "Missing required argument: amount_cents"
                args["amount_cents"] = self._to_int(arguments["amount_cents"], "amount_cents", 1, 10000000)
                if isinstance(args["amount_cents"], str):
                    return args["amount_cents"]

            elif tool_name == "advance_days":
                if "n" not in arguments:
                    return "Missing required argument: n"
                args["n"] = self._to_int(arguments["n"], "n", 1, 7)
                if isinstance(args["n"], str):
                    return args["n"]

        except Exception as e:
            return f"Argument validation error: {e}"

        return args

    def _to_int(self, value, name, min_val, max_val):
        """Convert value to int with bounds checking. Returns int or error string."""
        # Reject booleans (which are int subclass in Python)
        if isinstance(value, bool):
            return f"{name} must be an integer, not boolean"
        # Reject floats
        if isinstance(value, float):
            return f"{name} must be an integer, not float"
        # Accept int or string-encoded int
        if isinstance(value, int):
            v = value
        elif isinstance(value, str):
            try:
                v = int(value)
            except ValueError:
                return f"{name} must be an integer, got '{value}'"
        else:
            return f"{name} must be an integer"

        if v < min_val or v > max_val:
            return f"{name} must be between {min_val} and {max_val}, got {v}"
        return v

    def _handle_state(self):
        """Return current state hash."""
        global engine
        if engine is None:
            self._send_json({"error": "No game loaded"}, 400)
            return
        with engine_lock:
            h = engine.get_state_hash()
        self._send_json({"state_hash": h})


def main():
    port_raw = os.environ.get("SANDBOX_PORT", "8000").strip()
    port = int(port_raw) if port_raw else 8000
    server = HTTPServer(("0.0.0.0", port), SandboxHandler)
    print(f"Sandbox server running on port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
