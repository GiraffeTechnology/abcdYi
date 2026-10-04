"""Run the abcdYi API on an automatically selected port.

Usage:
    uv run python -m api.serve

API_PORT is optional. When it is empty or busy, a free port is chosen (never
443, which is owned by SSH on CTYun hosts). The chosen port is printed and,
if API_PORT_FILE is set, written to that file.
"""

from __future__ import annotations

import os

from src.aivan.utils.ports import serve


def main() -> None:
    serve(
        "api.main:app",
        host=os.environ.get("API_HOST", "127.0.0.1"),
        requested=os.environ.get("API_PORT"),
        env_var="API_PORT",
        file_env_var="API_PORT_FILE",
    )


if __name__ == "__main__":
    main()
