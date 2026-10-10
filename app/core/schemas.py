"""Validated configurations shared by the CLI, registry and execution engine."""
from typing import Any, Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator


class Record(BaseModel):
    id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    enabled: bool = True

    model_config = {'extra': 'forbid'}


class Model(Record):
    name: str = Field(min_length=1)
    provider: Literal['ollama', 'openai_compatible'] = 'ollama'
    model_name: str = Field(min_length=1)
    base_url: str = 'http://127.0.0.1:11434'
    context_length: int = Field(default=8192, ge=512, le=131072)
    notes: str = ''
    api_key_env: str | None = None
    thinking: bool = False

    @field_validator('base_url')
    @classmethod
    def valid_url(cls, value):
        u = urlparse(value)
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError('base_url must be an HTTP URL without credentials, query or fragment')
        return value.rstrip('/')

    @field_validator('api_key_env')
    @classmethod
    def valid_env_name(cls, value):
        import re
        if value is not None and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
            raise ValueError('invalid environment variable name')
        return value


class Tool(Record):
    description: str
    permission_level: Literal[1, 2] = 1
    parameters: dict[str, Any] = Field(default_factory=lambda: {'type': 'object', 'properties': {}, 'additionalProperties': False})


class Agent(Record):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    model_id: str
    fallback_model_id: str | None = None
    permission_level: Literal[1, 2] = 1
    tools: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
    knowledge_sources: list[str] = Field(default_factory=list)
    parent_id: str | None = None


class Assessment(BaseModel):
    """A factual, evidence-oriented recruitment report; not a hiring decision."""
    candidate: str
    role: str
    experience: str
    relevant_skills: list[str]
    strengths: list[str]
    gaps: list[str]
    concerns: list[str]
    questions_to_verify: list[str]
    recommended_practical_test_areas: list[str]
    assessment_summary: str
    model_config = {'extra': 'forbid'}
