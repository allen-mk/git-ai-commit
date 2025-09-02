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
    enabled: bool = Field(True, description="是否启用缓存")
    ttl_sec: int = Field(3600, description="缓存的生存时间（秒），默认为1小时")
    directory: str = Field("~/.cache/aicommit", description="缓存目录")


class HookConfig(BaseModel):
    enabled: bool = Field(True, description="是否在 Git Hook 中启用 aicommit")
    no_overwrite: bool = Field(False, description="如果提交信息文件已存在内容，则不覆盖")


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig, description="LLM 模型相关配置")
    formatter: FormatterConfig = Field(default_factory=FormatterConfig, description="格式化器相关配置")
    collectors: List[CollectorConfig] = Field(default_factory=list, description="收集器列表配置")
    output: OutputConfig = Field(default_factory=OutputConfig, description="输出相关配置")
    cache: CacheConfig = Field(default_factory=CacheConfig, description="缓存相关配置")
    hook: HookConfig = Field(default_factory=HookConfig, description="Git Hook 相关配置")
