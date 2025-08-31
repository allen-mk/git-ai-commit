from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class FileChange(BaseModel):
    path: str
    diff: str
    language: Optional[str] = None
    functions: Optional[List[str]] = None

class Context(BaseModel):
    files: List[FileChange] = []
    readme: Optional[str] = None
    recent_commits: List[str] = []
    issues: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}  # branch, repo, author, time, etc.
