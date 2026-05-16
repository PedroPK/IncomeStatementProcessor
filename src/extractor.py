"""Extract files from the input ZIP, handling filename encoding issues."""
import os
import zipfile
import tempfile
from pathlib import Path


def _is_metadata_entry(raw_name: str, safe_name: str, is_dir: bool) -> bool:
    """Return True for ZIP artifacts that should not be extracted."""
    if is_dir:
        return True

    parts = [part for part in raw_name.replace('\\', '/').split('/') if part]
    if '__MACOSX' in parts:
        return True

    if safe_name in {'.DS_Store', 'Thumbs.db'}:
        return True

    # macOS AppleDouble sidecar/resource-fork files
    if safe_name.startswith('._'):
        return True

    return False


def _safe_name(raw: str) -> str:
    """Normalise a ZIP entry filename to a safe filesystem path."""
    # Some ZIPs use CP437; try to decode properly
    try:
        decoded = raw.encode('cp437').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        decoded = raw
    # Remove directory components and replace unsafe chars
    return os.path.basename(decoded)


def extract_zip(zip_path: str) -> dict[str, str]:
    """Extract *zip_path* to a temporary directory.

    Returns a mapping ``{original_filename: absolute_path_on_disk}`` for every
    extracted entry, regardless of extension.
    """
    tmpdir = tempfile.mkdtemp(prefix='irpf_')
    result: dict[str, str] = {}

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            safe = _safe_name(info.filename)
            if not safe:
                continue
            if _is_metadata_entry(info.filename, safe, info.is_dir()):
                continue
            dest = os.path.join(tmpdir, safe)
            data = zf.read(info.filename)
            with open(dest, 'wb') as fh:
                fh.write(data)
            result[safe] = dest

    return result


def find_zip(input_dir: str) -> str | None:
    """Return the path of the first ZIP file found in *input_dir*."""
    for entry in Path(input_dir).iterdir():
        if entry.suffix.lower() == '.zip':
            return str(entry)
    return None
