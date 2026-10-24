"""Native project persistence; no GUI admission or content mutation."""

from .archive import ArchiveLimits, LoadedProject, read_archive, write_archive
from .duplicate import duplicate_project
from .service import FileHandle, PersistenceService, SaveResult

__all__ = [
    "ArchiveLimits",
    "LoadedProject",
    "read_archive",
    "write_archive",
    "duplicate_project",
    "FileHandle",
    "PersistenceService",
    "SaveResult",
]
