# Inputs Directory

This directory holds external instruction files provided to the agent harness.

## Specification Contract (Sections 05 & 06)
- **Run A (Demo Run)**: Uses standard prompt instructions without external appends.
- **Run B (Live Stress Test)**: The judges supply an undisclosed instruction file passed via the `APPEND_FILE` environment variable (default: `inputs/append.txt`).
- The contents of `APPEND_FILE` are appended directly to the end of the system prompt and logged to telemetry.
- If a specified `APPEND_FILE` is missing or empty, the run terminates immediately with exit code 3 (bad config).
