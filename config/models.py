from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ModelConfig(BaseModel):
    provider: str = "openai"
    name: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout_sec: int = 20
    stream: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)

class CollectorConfig(BaseModel):
    type: str
    options: Dict[str, Any] = Field(default_factory=dict)

class FormatterConfig(BaseModel):
    template: str = "conventional.j2"
    template_dir: Optional[str] = None

class OutputConfig(BaseModel):
    language: str = "en"
    max_subject_len: int = 72
    wrap_body_at: int = 100

class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_sec: int = 3600  # Default: 1 hour
    directory: str = "~/.cache/aicommit"


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    formatter: FormatterConfig = Field(default_factory=FormatterConfig)
    collectors: List[CollectorConfig] = Field(default_factory=list)
    output: OutputConfig = Field(default_factory=OutputConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
