"""Shared Groq structured-output client."""
from __future__ import annotations

import copy
import os
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from config import GROQ_MODEL_NAME

SchemaModel = TypeVar("SchemaModel", bound=BaseModel)


def _client() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to the project's .env file.")
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def strict_json_schema(model: type[SchemaModel]) -> dict:
    """Make Pydantic's schema compatible with Groq strict structured output."""
    schema = copy.deepcopy(model.model_json_schema())

    def visit(node: object) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                properties = node.get("properties", {})
                node["additionalProperties"] = False
                if properties:
                    node["required"] = list(properties)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def complete_json(
    *,
    prompt: str,
    response_model: type[SchemaModel],
    schema_name: str,
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
) -> str:
    """Return a Groq completion constrained to the supplied Pydantic schema."""
    extra_body = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
    response = _client().chat.completions.create(
        model=GROQ_MODEL_NAME,
        messages=[
            {"role": "system", "content": "Return only the requested structured JSON. Do not use tools."},
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": strict_json_schema(response_model),
            },
        },
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty structured response.")
    return content
