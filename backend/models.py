from pydantic import BaseModel
from typing import List, Optional


class FileInfo(BaseModel):
    id: str
    name: str
    size: int
    pages: int
    path: str
    session_id: Optional[str] = None
    error: Optional[str] = None


class FolioConfig(BaseModel):
    font_size: float = 11.0
    margin_top: float = 20.0
    margin_right: float = 30.0
    position: str = "top-right"
    foliar: bool = True
    folio_start: int = 1


class ProcessRequest(BaseModel):
    file_ids: List[str]
    config: FolioConfig
    output_name: Optional[str] = None
    nombre_expediente: Optional[str] = None


class FolderRequest(BaseModel):
    path: str


class CountRequest(BaseModel):
    file_ids: List[str]


# ── Expedition management models ───────────────────────────────────────────────

class ExpedienteConfigFolio(BaseModel):
    activo: bool = True
    posicion: str = "top-right"
    tamano: float = 11.0
    margen_superior: float = 20.0
    margen_lateral: float = 30.0
    iniciar_desde: int = 1


class CreateExpedienteRequest(BaseModel):
    nombre: str


class RenameExpedienteRequest(BaseModel):
    nombre_nuevo: str


class UpdateOrdenRequest(BaseModel):
    orden: List[str]


class UpdateConfigFolioRequest(BaseModel):
    config_folio: ExpedienteConfigFolio


class GenerarExpedienteRequest(BaseModel):
    output_name: str
    config_folio: Optional[ExpedienteConfigFolio] = None


class AppConfigRequest(BaseModel):
    carpeta_raiz: str
