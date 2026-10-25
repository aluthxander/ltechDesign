"""Runtime-only local/embedded resolution. Authored font records remain untouched."""

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QFontDatabase, QGuiApplication

from ltechdesign.domain.models import AssetId, FontId, Project, TextData

from .media import MediaSource, prepare_sources
from .text import Resources, clear_cache


@lru_cache(maxsize=1)
def system_font_files() -> tuple[tuple[str, Path], ...]:
    if os.name != "nt":
        return ()
    import winreg

    result: list[tuple[str, Path]] = []
    directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, key) as handle:
                for index in range(winreg.QueryInfoKey(handle)[1]):
                    name, filename, _ = winreg.EnumValue(handle, index)
                    if isinstance(filename, str):
                        path = Path(filename)
                        result.append(
                            (name.split(" (")[0], path if path.is_absolute() else directory / path)
                        )
        except OSError:
            continue
    return tuple(result)


def local_families() -> list[str]:
    if QGuiApplication.platformName() not in ("offscreen", "minimal"):
        return sorted(QFontDatabase.families())
    return sorted(set(QFontDatabase.families()) | {n for n, _ in system_font_files()})


def default_family() -> str:
    families = QFontDatabase.families()
    default = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    return (
        default
        if default in families
        else "Segoe UI"
        if "Segoe UI" in families
        else sorted(families)[0]
        if families
        else default
    )


class FontResolver:
    def __init__(self) -> None:
        self._registered: dict[str, tuple[int, tuple[str, ...]]] = {}
        self._system_registered: list[int] = []
        self._system_paths: set[Path] = set()
        self._system_families: set[str] = set()
        self.ensure_family("Segoe UI")  # Qt offscreen on Windows has no native font backend.

    def ensure_family(self, family: str) -> None:
        if family in self._system_families or (
            family in QFontDatabase.families()
            and QGuiApplication.platformName() not in ("offscreen", "minimal")
        ):
            return
        self._system_families.add(family)
        entries = sorted(
            system_font_files(), key=lambda pair: pair[0].casefold() != family.casefold()
        )
        for name, path in entries:
            if family.casefold() not in [
                part.strip().casefold() for part in name.split("&")
            ] and not name.casefold().startswith(family.casefold() + " "):
                continue
            if len(self._system_registered) >= 64:
                return
            if path in self._system_paths:
                continue
            self._system_paths.add(path)
            handle = QFontDatabase.addApplicationFont(str(path))
            if handle >= 0:
                self._system_registered.append(handle)
                clear_cache()

    def resolve(
        self,
        project: Project,
        blobs: Mapping[str, bytes] | None = None,
        *,
        media: Mapping[AssetId, MediaSource] | None = None,
    ) -> Resources:
        used = {
            n.data.typography.font_id
            for n in project.document.nodes.values()
            if isinstance(n.data, TextData)
        }
        texts = "".join(getattr(n.data, "text", "") for n in project.document.nodes.values())
        scripts = []
        if any(0x3400 <= ord(ch) <= 0x9FFF for ch in texts):
            scripts.append("Microsoft YaHei")
        if any(0x900 <= ord(ch) <= 0x97F for ch in texts):
            scripts.append("Nirmala UI")
        if any(0xE00 <= ord(ch) <= 0xEFF for ch in texts):
            scripts.append("Leelawadee UI")
        if any(ord(ch) >= 0x1F000 for ch in texts):
            scripts.append("Segoe UI Emoji")
        for font in project.fonts.fonts:
            if font.id not in used:
                continue
            for family in (font.family, *font.fallback_families, *scripts):
                self.ensure_family(family)
        # Register every embedded family before resolving fallback chains. A missing
        # system family may fall back to an embedded family later in the registry.
        assets = {a.id: a for a in project.assets.assets}
        for font in project.fonts.fonts:
            if font.id not in used or font.source != "embedded" or font.asset_id not in assets:
                continue
            asset = assets[font.asset_id]
            data = (blobs or {}).get(asset.path)
            if (
                asset.sha256 not in self._registered
                and data is not None
                and len(self._registered) < 64
            ):
                handle = QFontDatabase.addApplicationFontFromData(QByteArray(data))
                clear_cache()
                self._registered[asset.sha256] = (
                    handle,
                    tuple(QFontDatabase.applicationFontFamilies(handle)) if handle >= 0 else (),
                )
        available = set(QFontDatabase.families())
        aliases = {family.casefold(): family for family in available}
        default = default_family()
        families: dict[FontId, str] = {}
        fallback: dict[FontId, tuple[str, ...]] = {}
        notes: list[str] = []
        for font in project.fonts.fonts:
            if font.id not in used:
                continue
            primary = aliases.get(font.family.casefold(), font.family)
            if font.source == "embedded" and font.asset_id in assets:
                asset = assets[font.asset_id]
                registration = self._registered.get(asset.sha256)
                if registration and registration[1]:
                    primary = registration[1][0]
                    available.update(registration[1])
                else:
                    notes.append(f"embedded_font_unavailable:{font.id}")
            candidates = [
                aliases[f.casefold()]
                for f in (*font.fallback_families, *scripts)
                if f.casefold() in aliases
            ]
            if primary not in available:
                primary = candidates[0] if candidates else default
                notes.append(f"font_missing:{font.id}:{font.family} -> {primary}")
            families[font.id] = primary
            fallback[font.id] = tuple(dict.fromkeys([*candidates, default]))
        return Resources(
            families,
            fallback,
            tuple(notes),
            strict=False,
            media=media
            if media is not None
            else prepare_sources(project.assets.assets, blobs or {}),
        )

    def close(self) -> None:
        if self._registered or self._system_registered:
            clear_cache()
        for handle, _ in self._registered.values():
            if handle >= 0:
                QFontDatabase.removeApplicationFont(handle)
        self._registered.clear()
        for handle in self._system_registered:
            QFontDatabase.removeApplicationFont(handle)
        self._system_registered.clear()
        self._system_paths.clear()
        self._system_families.clear()
