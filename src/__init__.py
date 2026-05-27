import re
from pathlib import Path

def _read_version_from_changelog() -> str:
    """Parse the latest version from docs/CHANGELOG.md (first ## [X.Y.Z] line)."""
    changelog = Path(__file__).parent.parent / 'docs' / 'CHANGELOG.md'
    try:
        for line in changelog.read_text(encoding='utf-8').splitlines():
            m = re.match(r'^##\s+\[(\d+\.\d+\.\d+)\]', line)
            if m:
                return m.group(1)
    except OSError:
        pass
    return '0.0.0'

__version__ = _read_version_from_changelog()
