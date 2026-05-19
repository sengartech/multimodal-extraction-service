"""Small OpenAI Responses API client for structured outputs."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel
from openai import OpenAI

from scope_modeler.llm.schema import to_openai_strict_json_schema

T = TypeVar("T", bound=BaseModel)


class OpenAIStructuredClient:
    """OpenAI Responses API wrapper for strict JSON schema outputs."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required to use OpenAIStructuredClient. "
                "Unit tests should use fake model clients."
            )
        
        self.client = OpenAI(api_key=self.api_key)

    def run_text(
        self,
        *,
        model: str,
        schema_name: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:

        response = self.client.responses.create(
            model=model,
            instructions=system_prompt,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                }
            ],
            text=self._response_format(schema_name, response_model),
        )
        return self._parse_response(response, response_model)

    def run_image(
        self,
        *,
        model: str,
        schema_name: str,
        prompt: str,
        image_path: Path,
        response_model: type[T],
    ) -> T:

        response = self.client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": _image_to_data_url(Path(image_path)),
                            "detail": "auto",
                        },
                    ],
                }
            ],
            text=self._response_format(schema_name, response_model),
        )
        return self._parse_response(response, response_model)

    def _response_format(
        self,
        schema_name: str,
        response_model: type[BaseModel],
    ) -> dict[str, object]:
        return {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": to_openai_strict_json_schema(response_model.model_json_schema()),
                "strict": True,
            }
        }

    def _parse_response(self, response: object, response_model: type[T]) -> T:
        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise RuntimeError("OpenAI response did not include output_text JSON.")
        return response_model.model_validate(json.loads(output_text))


def _image_to_data_url(image_path: Path) -> str:
    media_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"
