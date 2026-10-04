"""Giraffe Agent helper entry point.
The FastAPI application entry point is:
    api.main:app
Run the API server on an automatically selected free port with:
    uv run python -m api.serve
Interactive API docs are served at /docs on the printed port.
"""


def main() -> None:
    print("Giraffe Agent")
    print("FastAPI entry point: api.main:app")
    print("Run: uv run python -m api.serve")
    print("Docs: /docs on the port printed at startup")


if __name__ == "__main__":
    main()
