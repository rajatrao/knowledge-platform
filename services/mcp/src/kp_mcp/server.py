"""Knowledge MCP server. Run with PYTHONPATH including the platform package."""

from kp.mcp_tools import build_server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
