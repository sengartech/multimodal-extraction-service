"""Local CLI entrypoint for the scaffold."""

from __future__ import annotations

import argparse

from scope_modeler import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scope-modeler",
        description="Local-first renovation scope extraction scaffold.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0
