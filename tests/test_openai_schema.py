from pydantic import BaseModel, ConfigDict, Field

from scope_modeler.llm.schema import to_openai_strict_json_schema


class NestedSchemaExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Nested name")
    tags: list[str] = Field(default_factory=list)


class SchemaExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(description="Example headline")
    nested: NestedSchemaExample
    optional_values: list[NestedSchemaExample] = Field(default_factory=list)


def test_openai_schema_removes_unsupported_keywords():
    strict_schema = to_openai_strict_json_schema(SchemaExample.model_json_schema())

    assert not _contains_key(strict_schema, "default")
    assert not _contains_key(strict_schema, "title")
    assert not _contains_key(strict_schema, "description")


def test_openai_schema_has_no_ref_sibling_keys():
    strict_schema = to_openai_strict_json_schema(SchemaExample.model_json_schema())

    assert not _contains_ref_with_siblings(strict_schema)


def test_openai_schema_sets_additional_properties_false_for_objects():
    strict_schema = to_openai_strict_json_schema(SchemaExample.model_json_schema())

    assert _objects_with_properties_have_no_extra_properties(strict_schema)


def test_openai_schema_required_contains_all_property_keys():
    strict_schema = to_openai_strict_json_schema(SchemaExample.model_json_schema())

    assert set(strict_schema["required"]) == set(strict_schema["properties"].keys())
    nested_schema = strict_schema["$defs"]["NestedSchemaExample"]
    assert set(nested_schema["required"]) == set(nested_schema["properties"].keys())


def _contains_key(node, key: str) -> bool:
    if isinstance(node, dict):
        return key in node or any(_contains_key(value, key) for value in node.values())
    if isinstance(node, list):
        return any(_contains_key(item, key) for item in node)
    return False


def _contains_ref_with_siblings(node) -> bool:
    if isinstance(node, dict):
        if "$ref" in node and set(node.keys()) != {"$ref"}:
            return True
        return any(_contains_ref_with_siblings(value) for value in node.values())
    if isinstance(node, list):
        return any(_contains_ref_with_siblings(item) for item in node)
    return False


def _objects_with_properties_have_no_extra_properties(node) -> bool:
    if isinstance(node, dict):
        if "properties" in node and node.get("additionalProperties") is not False:
            return False
        return all(_objects_with_properties_have_no_extra_properties(value) for value in node.values())
    if isinstance(node, list):
        return all(_objects_with_properties_have_no_extra_properties(item) for item in node)
    return True
