"""
Gestión de carpetas temporales por sesión.

Estructura en disco:
    temp/
        session_<uuid>/        ← una por expediente
            <file_uuid>.pdf
            <file_uuid>.pdf
            ...

Reglas de seguridad:
  - El session_id debe ser un UUID válido.
  - Solo se permite borrar dentro de temp/.
  - Nunca se borra la carpeta base temp/.
"""

import re
import shutil
import uuid
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# UUID v4 exacto — previene path traversal y nombres arbitrarios
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class SessionManager:
    """
    Crea, gestiona y limpia carpetas temporales de sesión de forma segura.
    Una instancia es suficiente para toda la aplicación (singleton).
    """

    def __init__(self, base: Path) -> None:
        self.base = base.resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        logger.info("[session] base temp: %s", self.base)

    # ── API pública ────────────────────────────────────────────────────────────

    def create(self) -> str:
        """Crea una nueva carpeta de sesión y devuelve su ID."""
        sid = str(uuid.uuid4())
        self._dir(sid).mkdir(parents=True, exist_ok=True)
        logger.info("[session] creada  → %s", sid)
        return sid

    def exists(self, session_id: str) -> bool:
        """True si la sesión tiene una carpeta activa en disco."""
        return self._is_valid(session_id) and self._dir(session_id).exists()

    def file_path(self, session_id: str, filename: str) -> Path:
        """
        Ruta completa para un archivo dentro de una sesión.
        Valida el session_id antes de construir el path.
        """
        if not self._is_valid(session_id):
            raise ValueError(f"session_id inválido: {session_id!r}")
        return self._dir(session_id) / filename

    def cleanup(self, session_id: str) -> bool:
        """
        Elimina de forma segura la carpeta de sesión y todo su contenido.
        - Valida el formato del ID.
        - Confirma que el path está dentro de temp/ antes de borrar.
        - Devuelve True si se limpió (o ya no existía), False si hubo error.
        """
        if not self._is_valid(session_id):
            logger.warning("[session] cleanup rechazado — ID inválido: %r", session_id)
            return False

        session_dir = self._dir(session_id)

        # Guardia de path traversal: el path resuelto debe estar dentro de base
        try:
            session_dir.resolve().relative_to(self.base)
        except ValueError:
            logger.error(
                "[session] ALERTA — intento de borrado fuera de temp/: %s", session_dir
            )
            return False

        if not session_dir.exists():
            return True  # ya no existe, no es un error

        try:
            shutil.rmtree(session_dir)
            logger.info("[session] eliminada → %s", session_id)
            return True
        except Exception as exc:
            logger.error("[session] error eliminando %s: %s", session_id, exc)
            return False

    def cleanup_stale(self, max_age_hours: int = 24) -> int:
        """
        Elimina sesiones inactivas más antiguas que max_age_hours.
        Se llama en el arranque de la aplicación.
        Devuelve el número de sesiones eliminadas.
        """
        cutoff   = datetime.now().timestamp() - max_age_hours * 3600
        removed  = 0

        for d in self.base.iterdir():
            if not (d.is_dir() and d.name.startswith("session_")):
                continue
            try:
                if d.stat().st_mtime < cutoff:
                    shutil.rmtree(d)
                    removed += 1
                    logger.info("[session] obsoleta eliminada → %s", d.name)
            except Exception as exc:
                logger.warning("[session] no se pudo limpiar %s: %s", d.name, exc)

        return removed

    def active_sessions(self) -> list[str]:
        """Devuelve los IDs de sesiones activas en disco."""
        return [
            d.name.removeprefix("session_")
            for d in self.base.iterdir()
            if d.is_dir() and d.name.startswith("session_")
        ]

    # ── Internos ───────────────────────────────────────────────────────────────

    def _dir(self, session_id: str) -> Path:
        return self.base / f"session_{session_id}"

    @staticmethod
    def _is_valid(session_id: str) -> bool:
        return isinstance(session_id, str) and bool(_UUID_RE.match(session_id))
