"""
Agent interface and mock agents for the Seasonal Farm Market.
"""
import json
import os
import sys
import re
import time
import urllib.request
import urllib.error


# ======================== REAL LLM AGENT ========================

class LLMAgent:
    """Agent that calls an LLM API."""

    def __init__(self, model, api_key, base_url, tools, system_prompt, max_tokens=None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens or 4096
        self.messages = [{"role": "system", "content": system_prompt}]
        self.parse_mode = "native"

    def get_response(self, observation=None):
        """
        Send observation to LLM and get response with tool calls.
        Returns (raw_response, parsed_tool_calls, parse_mode, token_info).
        Each tool call is {"name": str, "arguments": dict}.
        """
        if observation is not None:
            # Only append user observation if last message is not already a tool message
            if not (self.messages and self.messages[-1].get("role") == "tool"):
                self.messages.append({"role": "user", "content": observation})

        request_body = {
            "model": self.model,
            "messages": self.messages,
            "tools": self.tools,
            "tool_choice": "auto",
            "max_tokens": self.max_tokens,
        }

        raw_response = self._call_api(request_body)
        if raw_response is None:
            return None, [], "error", {}

        # Parse the response
        choice = raw_response.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = raw_response.get("usage") or {}

        # Try native tool_calls first
        tool_calls = []
        self.parse_mode = "native"

        native_calls = message.get("tool_calls", [])
        if native_calls:
            for tc in native_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                if isinstance(raw_args, dict):
                    args = raw_args
                elif isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                else:
                    args = {}
                tool_calls.append({"id": tc.get("id", ""), "name": name, "arguments": args})
        else:
            # Fallback: parse tool calls from message content
            content = message.get("content", "")
            if content:
                parsed = self._parse_text_tool_calls(content)
                if parsed:
                    self.parse_mode = "text_fallback"
                    tool_calls = parsed

        # Add assistant message to history
        self.messages.append(message)

        p_tok = usage.get("prompt_tokens", 0) or 0
        c_tok = usage.get("completion_tokens", 0) or 0
        t_tok = usage.get("total_tokens", p_tok + c_tok) or (p_tok + c_tok)

        token_info = {
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "total_tokens": t_tok,
        }

        return raw_response, tool_calls, self.parse_mode, token_info

    def add_tool_result(self, tool_call_id, result):
        """Add a tool result to conversation history (only in native function calling mode)."""
        content_str = str(result)
        # Cap tool output length to prevent single-call context flooding
        if len(content_str) > 2000:
            content_str = content_str[:2000] + "\n... (truncated tool output)"

        if self.parse_mode == "native":
            self.messages.append({
                "role": "tool",
                "tool_call_id": str(tool_call_id),
                "content": content_str,
            })

    def add_observation(self, text):
        """Add an observation as a user message."""
        content_str = str(text)
        if len(content_str) > 2500:
            content_str = content_str[:2500] + "\n... (truncated observation)"
        self.messages.append({"role": "user", "content": content_str})

    def trim_history(self, max_chars=32000):
        """
        Compress older turns and keep total context well within safe token bounds (< 64K).
        Preserves system prompt (index 0) and keeps the last 3 turns completely uncompressed.
        Compresses observations in earlier turns to a 1-line summary.
        """
        # 1. Observation compression for older turns (before the last 6 messages)
        if len(self.messages) > 8:
            cutoff = len(self.messages) - 6
            for idx in range(1, cutoff):
                msg = self.messages[idx]
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > 160:
                    first_line = content.split("\n", 1)[0][:120]
                    msg["content"] = f"[Past Step Summary: {first_line}...]"

        # 2. Character-budget trimming if still exceeding max_chars
        total = sum(len(json.dumps(m)) for m in self.messages)
        while total > max_chars and len(self.messages) > 6:
            removed = self.messages.pop(1)
            total -= len(json.dumps(removed))
            while len(self.messages) > 3 and self.messages[1].get("role") in ("assistant", "tool"):
                removed = self.messages.pop(1)
                total -= len(json.dumps(removed))

        # Invariant check: message directly after system must NEVER be an orphaned tool message
        while len(self.messages) > 2 and self.messages[1].get("role") == "tool":
            self.messages.pop(1)

    def _call_api(self, request_body):
        """Call the LLM API with retries for token format errors, rate limits, and network timeouts."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                data = json.dumps(request_body).encode("utf-8")
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=data,
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                print(f"[API HTTPError {e.code}] {error_body[:300]}", file=sys.stderr, flush=True)
                # If max_tokens rejected, retry with max_completion_tokens
                if attempt == 0 and "max_tokens" in error_body.lower():
                    mt = request_body.pop("max_tokens", 4096)
                    request_body["max_completion_tokens"] = mt
                    continue
                # Transient HTTP server errors or rate limits
                if e.code in (429, 500, 502, 503, 504) and attempt < max_attempts - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return None
            except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as e:
                print(f"[API Network/Timeout (attempt {attempt+1}/{max_attempts})]: {e}", file=sys.stderr, flush=True)
                if attempt < max_attempts - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return None
            except Exception as e:
                print(f"[API Error] {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                return None
        return None

    def _parse_text_tool_calls(self, content):
        """
        Parse tool calls from message text.
        Handles JSON object/list with name/arguments or tool/args keys,
        optionally in a fenced code block.
        """
        # Strip fenced code blocks
        code_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        text = code_match.group(1) if code_match else content

        # Try to find JSON
        calls = []

        # Try parsing as JSON array or object
        for candidate in self._extract_json_candidates(text):
            try:
                parsed = json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                continue

            if isinstance(parsed, list):
                for item in parsed:
                    tc = self._normalize_tool_call(item)
                    if tc:
                        calls.append(tc)
            elif isinstance(parsed, dict):
                tc = self._normalize_tool_call(parsed)
                if tc:
                    calls.append(tc)

            if calls:
                break

        return calls

    def _extract_json_candidates(self, text):
        """Extract potential JSON strings from text."""
        candidates = []
        # Full text
        text = text.strip()
        candidates.append(text)

        # Find JSON objects/arrays
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            depth = 0
            start = None
            for i, ch in enumerate(text):
                if ch == start_char:
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0 and start is not None:
                        candidates.append(text[start:i + 1])
                        start = None

        return candidates

    def _normalize_tool_call(self, obj):
        """Normalize a parsed JSON object to a tool call dict."""
        if not isinstance(obj, dict):
            return None

        name = obj.get("name") or obj.get("tool") or obj.get("function")
        args = obj.get("arguments") or obj.get("args") or obj.get("parameters") or {}

        if not name or not isinstance(name, str):
            return None

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, ValueError):
                args = {}

        if not isinstance(args, dict):
            args = {}

        return {"id": "", "name": name, "arguments": args}


# ======================== MOCK AGENTS ========================

class MockSolverAgent:
    """Replays oracle actions as real tool calls, max 10 per reply."""

    def __init__(self, oracle_actions):
        self.actions = list(oracle_actions)
        self.index = 0
        self.parse_mode = "native"

    def get_response(self, observation=None):
        """Return next batch of oracle actions (up to 10)."""
        batch = []
        count = 0
        while self.index < len(self.actions) and count < 10:
            name, args = self.actions[self.index]
            self.index += 1
            batch.append({"id": f"call_{self.index}", "name": name, "arguments": args})
            count += 1

        if not batch:
            batch = [{"id": "call_finish", "name": "finish", "arguments": {}}]

        return {"mock": True}, batch, "native", {"prompt_tokens": 0, "completion_tokens": 0}

    def add_tool_result(self, tool_call_id, result):
        pass

    def add_observation(self, text):
        pass

    def trim_history(self, max_chars=40000):
        pass


class MockIdleAgent:
    """Calls finish immediately."""

    def __init__(self):
        self.parse_mode = "native"
        self._done = False

    def get_response(self, observation=None):
        if not self._done:
            self._done = True
            return (
                {"mock": True},
                [{"id": "call_finish", "name": "finish", "arguments": {}}],
                "native",
                {"prompt_tokens": 0, "completion_tokens": 0}
            )
        return {"mock": True}, [], "native", {"prompt_tokens": 0, "completion_tokens": 0}

    def add_tool_result(self, tool_call_id, result):
        pass

    def add_observation(self, text):
        pass

    def trim_history(self, max_chars=40000):
        pass


class MockChaosAgent:
    """
    Sends malformed JSON, unknown tools, wrong types, huge numbers,
    50 calls in one reply, calls after game over.
    Must end WITHOUT crashing.
    """

    def __init__(self):
        self.parse_mode = "native"
        self.step = 0
        self._chaos_sequence = [
            # Malformed: unknown tool
            [{"id": "c1", "name": "explode", "arguments": {}}],
            # Wrong types
            [{"id": "c2", "name": "plant", "arguments": {"plot_id": "not_a_number", "crop": 12345}}],
            # Huge numbers
            [{"id": "c3", "name": "sell", "arguments": {"crop": "wheat", "quantity": 10**9}}],
            [{"id": "c4", "name": "advance_days", "arguments": {"n": 10**9}}],
            # Bool as int
            [{"id": "c5", "name": "plant", "arguments": {"plot_id": True, "crop": "wheat"}}],
            # Float
            [{"id": "c6", "name": "sell", "arguments": {"crop": "wheat", "quantity": 3.14}}],
            # 50 calls in one reply
            [{"id": f"c{i}", "name": "get_status", "arguments": {}} for i in range(50)],
            # Negative numbers
            [{"id": "c7", "name": "take_loan", "arguments": {"amount_cents": -1000}}],
            # Valid action then finish
            [{"id": "c8", "name": "get_status", "arguments": {}},
             {"id": "c9", "name": "finish", "arguments": {}}],
            # Calls after game over
            [{"id": "c10", "name": "plant", "arguments": {"plot_id": 0, "crop": "wheat"}}],
        ]

    def get_response(self, observation=None):
        if self.step < len(self._chaos_sequence):
            calls = self._chaos_sequence[self.step]
            self.step += 1
            return {"mock": True}, calls, "native", {"prompt_tokens": 0, "completion_tokens": 0}

        # Final: finish if not already done
        self.step += 1
        return (
            {"mock": True},
            [{"id": "final", "name": "finish", "arguments": {}}],
            "native",
            {"prompt_tokens": 0, "completion_tokens": 0}
        )

    def add_tool_result(self, tool_call_id, result):
        pass

    def add_observation(self, text):
        pass

    def trim_history(self, max_chars=40000):
        pass


class MockTextAgent:
    """
    Sends tool calls as JSON text in message content (no native tool_calls)
    to exercise the fallback parser.
    """

    def __init__(self, oracle_actions):
        self.actions = list(oracle_actions)
        self.index = 0
        self.parse_mode = "text_fallback"
        self._done = False

    def get_response(self, observation=None):
        if self._done or self.index >= len(self.actions):
            self._done = True
            content = json.dumps({"name": "finish", "arguments": {}})
            return (
                {"mock": True, "choices": [{"message": {"content": content}}]},
                [{"id": "text_finish", "name": "finish", "arguments": {}}],
                "text_fallback",
                {"prompt_tokens": 0, "completion_tokens": 0}
            )

        batch = []
        count = 0
        while self.index < len(self.actions) and count < 10:
            name, args = self.actions[self.index]
            self.index += 1
            batch.append({"name": name, "arguments": args})
            count += 1

        content = "```json\n" + json.dumps(batch) + "\n```"
        parsed = [{"id": f"text_{i}", "name": b["name"], "arguments": b["arguments"]}
                   for i, b in enumerate(batch)]

        return (
            {"mock": True, "choices": [{"message": {"content": content}}]},
            parsed,
            "text_fallback",
            {"prompt_tokens": 0, "completion_tokens": 0}
        )

    def add_tool_result(self, tool_call_id, result):
        pass

    def add_observation(self, text):
        pass

    def trim_history(self, max_chars=40000):
        pass


def create_agent(model, task_instance, tools, system_prompt):
    """Create the appropriate agent based on MODEL env var."""
    if model == "mock/solver":
        return MockSolverAgent(task_instance.oracle_actions)
    elif model == "mock/idle":
        return MockIdleAgent()
    elif model == "mock/chaos":
        return MockChaosAgent()
    elif model == "mock/text":
        return MockTextAgent(task_instance.oracle_actions)
    else:
        api_key = os.environ.get("API_KEY", "")
        base_url = os.environ.get("BASE_URL", "https://api.openai.com/v1")
        max_tokens_raw = os.environ.get("MAX_TOKENS", "").strip()
        try:
            max_tokens = int(max_tokens_raw) if max_tokens_raw else None
        except ValueError:
            max_tokens = None
        return LLMAgent(model, api_key, base_url, tools, system_prompt, max_tokens)
