"""Opt-in updater for signed-off public GitHub Releases."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

REPOSITORY = "spsstudiohu/sps-lut-editor"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
INSTALLER_NAME = "SPS-LUT-Editor-Setup.exe"
CHECKSUM_NAME = INSTALLER_NAME + ".sha256"


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    notes: str
    installer_url: str
    checksum_url: str


def _version_key(value: str) -> tuple[int, ...]:
    value = value.strip().lstrip("vV")
    try:
        return tuple(int(part) for part in value.split("."))
    except ValueError as exc:
        raise UpdateError(f"Érvénytelen kiadási verzió: {value}") from exc


def is_newer(remote: str, current: str) -> bool:
    remote_key, current_key = _version_key(remote), _version_key(current)
    width = max(len(remote_key), len(current_key))
    return remote_key + (0,) * (width - len(remote_key)) > current_key + (0,) * (width - len(current_key))


def latest_release(timeout: int = 8) -> Release:
    request = Request(API_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "SPS-LUT-Editor"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (URLError, OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"A GitHub kiadások nem érhetők el: {exc}") from exc
    assets = {asset.get("name"): asset.get("browser_download_url") for asset in payload.get("assets", [])}
    installer, checksum = assets.get(INSTALLER_NAME), assets.get(CHECKSUM_NAME)
    if not installer or not checksum:
        raise UpdateError(f"A legújabb kiadás nem tartalmazza a {INSTALLER_NAME} és {CHECKSUM_NAME} fájlokat.")
    return Release(str(payload.get("tag_name", "")), str(payload.get("body", "")), installer, checksum)


def download_verified(release: Release, destination: str | Path, timeout: int = 60) -> Path:
    """Download only after matching the SHA-256 published with the same release."""
    request_headers = {"User-Agent": "SPS-LUT-Editor"}
    try:
        with urlopen(Request(release.checksum_url, headers=request_headers), timeout=timeout) as response:
            expected = response.read().decode("ascii").strip().split()[0].lower()
        with urlopen(Request(release.installer_url, headers=request_headers), timeout=timeout) as response:
            data = response.read()
    except (URLError, OSError, UnicodeDecodeError) as exc:
        raise UpdateError(f"A frissítés letöltése nem sikerült: {exc}") from exc
    actual = sha256(data).hexdigest()
    if len(expected) != 64 or actual != expected:
        raise UpdateError("A letöltött telepítő SHA-256 ellenőrzése sikertelen; a telepítő nem indul el.")
    target = Path(destination)
    try:
        target.write_bytes(data)
    except OSError as exc:
        raise UpdateError(f"A frissítő nem menthető: {exc}") from exc
    return target
