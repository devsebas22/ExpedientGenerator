from pydantic import BaseModel
from typing import List, Optional


class FileInfo(BaseModel):
    id: str
    name: str
    size: int
    pages: int
    path: str
    session_id: Optional[str] = None   # carpeta temporal de origen
    error: Optional[str] = None


class FolioConfig(BaseModel):
    font_size: float = 11.0
    margin_top: float = 20.0
    margin_right: float = 30.0
    position: str = "top-right"  # top-right | top-left | bottom-right | bottom-left


class ProcessRequest(BaseModel):
    file_ids: List[str]
    config: FolioConfig
    output_name: Optional[str] = None


class FolderRequest(BaseModel):
    path: str


class CountRequest(BaseModel):
    file_ids: List[str]
