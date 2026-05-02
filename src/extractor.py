"""Extract files from the input ZIP, handling filename encoding issues."""
import os
import zipfile
import tempfile
from pathlib import Path


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
