"""JSON schema helpers for OpenAI strict structured outputs."""

from __future__ import annotations

from copy import deepcopy


def to_openai_strict_json_schema(schema: dict[str, object]) -> dict[str, object]:
    strict_schema = deepcopy(schema)
    _make_schema_node_strict(strict_schema)
    return strict_schema


def _make_schema_node_strict(node: object) -> None:
    if isinstance(node, dict):
        for keyword in ("default", "title", "examples", "description"):
            node.pop(keyword, None)

        if "$ref" in node:
            ref = node["$ref"]
            node.clear()
            node["$ref"] = ref
            return

        properties = node.get("properties")
        if isinstance(properties, dict):
            node["required"] = list(properties.keys())
            node["additionalProperties"] = False

        for key in ("$defs", "properties"):
            child_mapping = node.get(key)
            if isinstance(child_mapping, dict):
                for child in child_mapping.values():
                    _make_schema_node_strict(child)

        items = node.get("items")
        if items is not None:
            _make_schema_node_strict(items)

        for key in ("anyOf", "oneOf", "allOf"):
            variants = node.get(key)
            if isinstance(variants, list):
                for variant in variants:
                    _make_schema_node_strict(variant)
    elif isinstance(node, list):
        for item in node:
            _make_schema_node_strict(item)

