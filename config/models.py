from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ModelConfig(BaseModel):
    provider: str = "openai"
    name: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    timeout_sec: int = 20

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

class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    formatter: FormatterConfig = Field(default_factory=FormatterConfig)
    collectors: List[CollectorConfig] = Field(default_factory=list)
    output: OutputConfig = Field(default_factory=OutputConfig)
