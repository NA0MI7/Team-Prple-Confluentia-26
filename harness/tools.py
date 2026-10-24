"""
Tool definitions and argument validation for the Seasonal Farm Market.
"""


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get current game status: day, cash, debt, storage, plots, inventory.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market",
            "description": "Get today's market prices per crop, optionally with price history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_days": {
                        "type": "integer",
                        "description": "Number of past days to show (0-7). Default 0.",
                        "minimum": 0,
                        "maximum": 7,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Get a noisy 5-day price forecast.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get news announcements about upcoming events (droughts, demand spikes).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plant",
            "description": "Plant a crop on a plot. Costs seed money immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plot_id": {
                        "type": "integer",
                        "description": "The plot number to plant on.",
                    },
                    "crop": {
                        "type": "string",
                        "description": "Name of the crop to plant.",
                    },
                },
                "required": ["plot_id", "crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "harvest",
            "description": "Harvest a ready crop from a plot. Adds units to inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plot_id": {
                        "type": "integer",
                        "description": "The plot number to harvest from.",
                    },
                },
                "required": ["plot_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sell",
            "description": "Sell inventory at today's market price (with slippage). Oldest units sold first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {
                        "type": "string",
                        "description": "Name of the crop to sell.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of units to sell (>= 1).",
                        "minimum": 1,
                    },
                },
                "required": ["crop", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_loan",
            "description": "Take a loan (in cents). Only available on tasks with loans enabled.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount_cents": {
                        "type": "integer",
                        "description": "Loan amount in cents.",
                        "minimum": 1,
                    },
                },
                "required": ["amount_cents"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repay",
            "description": "Repay debt (in cents).",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount_cents": {
                        "type": "integer",
                        "description": "Amount to repay in cents.",
                        "minimum": 1,
                    },
                },
                "required": ["amount_cents"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "advance_days",
            "description": "Advance time by n days (1-7). Applies daily taxes, interest, and spoilage. TIP: advance_days accepts up to 7 days, and you can batch up to 10 tool calls per reply to plan and execute multi-step routines within step limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of days to advance (1-7). You can advance up to 7 days in a single call.",
                        "minimum": 1,
                        "maximum": 7,
                    },
                },
                "required": ["n"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "End the game early. Remaining days auto-simulate (taxes, interest, spoilage still apply).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def get_tool_names():
    """Return set of valid tool names."""
    return {t["function"]["name"] for t in TOOL_SCHEMAS}


def check_args(tool_name, arguments):
    """
    Validate tool arguments with typed checking.
    Returns (cleaned_args, None) on success or (None, error_string) on failure.
    """
    if not isinstance(arguments, dict):
        return None, "Arguments must be a JSON object."

    schema = None
    for t in TOOL_SCHEMAS:
        if t["function"]["name"] == tool_name:
            schema = t["function"]["parameters"]
            break
    if schema is None:
        return None, f"Unknown tool: {tool_name}"

    props = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields
    for r in required:
        if r not in arguments:
            return None, f"Missing required argument: {r}"

    # Reject unexpected keys
    unexpected = set(arguments.keys()) - set(props.keys())
    if unexpected:
        return None, f"Unexpected arguments: {', '.join(sorted(unexpected))}"

    cleaned = {}
    for key, val in arguments.items():
        if key not in props:
            continue
        prop = props[key]
        ptype = prop.get("type")

        if ptype == "integer":
            v, err = _to_int(val, key)
            if err:
                return None, err
            # Bounds
            if "minimum" in prop and v < prop["minimum"]:
                return None, f"{key} must be >= {prop['minimum']}, got {v}"
            if "maximum" in prop and v > prop["maximum"]:
                return None, f"{key} must be <= {prop['maximum']}, got {v}"
            cleaned[key] = v

        elif ptype == "string":
            if not isinstance(val, str):
                return None, f"{key} must be a string, got {type(val).__name__}"
            if len(val) > 100:
                return None, f"{key} too long (max 100 chars)"
            cleaned[key] = val

        else:
            cleaned[key] = val

    return cleaned, None


def _to_int(value, name):
    """Convert to int with strict type checking. Returns (int, None) or (None, error)."""
    if isinstance(value, bool):
        return None, f"{name} must be an integer, not boolean"
    if isinstance(value, float):
        return None, f"{name} must be an integer, not float"
    if isinstance(value, int):
        return value, None
    if isinstance(value, str):
        try:
            return int(value), None
        except ValueError:
            return None, f"{name} must be an integer, got '{value}'"
    return None, f"{name} must be an integer, got {type(value).__name__}"
