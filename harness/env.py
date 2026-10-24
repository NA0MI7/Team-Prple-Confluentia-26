"""
Environment wrapper: manages sandbox communication and harness-side replay scoring.
"""
import json
import copy
import time
import urllib.request
import urllib.error
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simcore.engine import Engine


SANDBOX_URL = os.environ.get("SANDBOX_URL", "http://sandbox:8000")
TOOL_TIMEOUT = 60  # seconds per tool call


class Environment:
    """
    Wraps sandbox communication and maintains harness-side replay engine.
    Scoring replays the action log through the harness engine from seeded start,
    so a misbehaving sandbox can never forge the score.
    """

    def __init__(self, task_instance):
        self.task = task_instance
        self.world = task_instance.get_world_for_sandbox()

        # Harness-side engine for replay scoring
        self.harness_engine = Engine(copy.deepcopy(self.world))

        # Action log for replay
        self.action_log = []
        self.done = False
        self.sandbox_errors = 0  # consecutive sandbox errors
        self.flags = []  # per-step flags
        self.consecutive_invalid = 0
        self.suspicious_count = 0
        self.invalid_actions_count = 0

    def reset(self):
        """Reset the sandbox engine via /reset."""
        try:
            data = json.dumps({"world": self.world}).encode("utf-8")
            req = urllib.request.Request(
                f"{SANDBOX_URL}/reset",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())

            if result.get("status") != "ok":
                raise RuntimeError(f"Reset failed: {result}")

            # Verify initial state hash matches
            sandbox_hash = result.get("state_hash", "")
            harness_hash = self.harness_engine.get_state_hash()
            if sandbox_hash != harness_hash:
                self.flags.append("initial_state_divergence")
                self.suspicious_count += 1

            self.sandbox_errors = 0
            return True
        except Exception as e:
            self.sandbox_errors += 1
            return False

    def step(self, tool_name, arguments):
        """
        Execute a tool call.
        Returns (observation_text, is_error, done).
        """
        step_flags = []

        # Flag suspicious behavior
        if tool_name not in {
            "get_status", "get_market", "get_forecast", "get_news",
            "plant", "harvest", "sell", "take_loan", "repay",
            "advance_days", "finish"
        }:
            step_flags.append("unknown_tool")

        # Check for calls after game over
        if self.done:
            step_flags.append("call_after_done")
            self.flags = step_flags
            self.suspicious_count += 1
            print(f"\n[SECURITY WARNING] Flagged suspicious behavior: call_after_done on {tool_name} | Total flags: {self.suspicious_count}", file=sys.stderr, flush=True)
            return "Game is already over. No more actions allowed.", True, True

        # Check for suspicious numeric arguments (negatives, floats where int expected, huge bounds)
        for k, v in arguments.items():
            if isinstance(v, (int, float)) and abs(v) > 10000000:
                step_flags.append("sane_bound_exceeded")
            if k in ("quantity", "amount_cents", "n") and isinstance(v, (int, float)) and v <= 0:
                step_flags.append(f"negative_or_zero_{k}")

        # Execute on sandbox
        try:
            data = json.dumps({"tool": tool_name, "arguments": arguments}).encode("utf-8")
            req = urllib.request.Request(
                f"{SANDBOX_URL}/execute",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=TOOL_TIMEOUT) as resp:
                result = json.loads(resp.read())

            self.sandbox_errors = 0
            obs = result.get("result", "No result")
            is_error = result.get("is_error", False)
            done = result.get("done", False)
            sandbox_hash = result.get("state_hash", "")

        except Exception as e:
            self.sandbox_errors += 1
            if self.sandbox_errors >= 2:
                self.done = True
                step_flags.append("sandbox_unreachable")
                self.flags = step_flags
                return f"Sandbox unreachable: {e}", True, True
            step_flags.append("sandbox_error")
            self.flags = step_flags
            return f"Sandbox error (will retry): {e}", True, False

        # Track invalid calls
        if is_error:
            self.invalid_actions_count += 1
            self.consecutive_invalid += 1
            if self.consecutive_invalid >= 3:
                step_flags.append(f"{self.consecutive_invalid}_consecutive_invalid")
        else:
            self.consecutive_invalid = 0

        if step_flags:
            self.suspicious_count += len(step_flags)
            for flag in step_flags:
                print(f"\n[SECURITY WARNING] Flagged suspicious behavior: {flag} on {tool_name}({arguments}) | Total flags: {self.suspicious_count}", file=sys.stderr, flush=True)

        # Replay on harness engine (only state-changing actions)
        state_changing = {"plant", "harvest", "sell", "take_loan", "repay", "advance_days", "finish"}
        if tool_name in state_changing and not is_error:
            self.action_log.append((tool_name, arguments))
            try:
                method = getattr(self.harness_engine, tool_name)
                method(**arguments)
            except Exception:
                step_flags.append("harness_replay_error")

            # Compare state hashes
            harness_hash = self.harness_engine.get_state_hash()
            if sandbox_hash and harness_hash != sandbox_hash:
                step_flags.append("state_divergence")

        if done:
            self.done = True

        # Truncate observation
        if len(obs) > 4000:
            obs = obs[:4000] + "\n... (truncated)"

        self.flags = step_flags
        return obs, is_error, done

    def score(self):
        """
        Compute final score by REPLAYING the action log through a fresh harness engine.
        This ensures sandbox can never forge the score.
        """
        # Fresh engine from the same world
        replay_engine = Engine(copy.deepcopy(self.world))

        for tool_name, arguments in self.action_log:
            try:
                method = getattr(replay_engine, tool_name)
                method(**arguments)
            except Exception:
                pass  # Skip invalid replay actions

        # Ensure game is done
        if not replay_engine.is_done():
            replay_engine.finish()

        return replay_engine.compute_score(self.task.oracle_gain)

    def get_step_reward(self):
        """
        Compute the score if the agent stopped now and idled to the horizon.
        Uses a scratch copy of the harness engine.
        """
        scratch = Engine({
            "cfg": copy.deepcopy(self.world["cfg"]),
            "prices": copy.deepcopy(self.world["prices"]),
            "events": copy.deepcopy(self.world["events"]),
            "initial_state": copy.deepcopy(self.world["initial_state"]),
        })

        # Replay action log
        for tool_name, arguments in self.action_log:
            try:
                method = getattr(scratch, tool_name)
                method(**arguments)
            except Exception:
                pass

        # Finish (idle to horizon)
        if not scratch.is_done():
            scratch.finish()

        return scratch.compute_score(self.task.oracle_gain)

    def get_harness_state_hash(self):
        """Return the harness engine's state hash."""
        return self.harness_engine.get_state_hash()
