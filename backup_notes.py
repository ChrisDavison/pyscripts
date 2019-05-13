#!/usr/bin/env python
"""Backup all notes (copy to another dir).

May update this in future to also zip."""
from datetime import date

from pathlib import Path


def main(outdir, note_format="*.org"):
    """Copy all notes with format FORMAT to outdir."""
    dropbox = Path('e:/Dropbox/')

    files = [f for f in dropbox.rglob(note_format) if 'dropbox.cache' not in str(f)]
    files.extend([f for f in dropbox.rglob('*') if 'assets' in str(f) and f.is_file()])

    outdir = Path('e:/Downloads/standalone-notes-backup/')

    for path in files:
        out = outdir / path.relative_to(dropbox)
        if not out.parent.exists():
            out.parent.mkdir(parents=True)
        if out.exists():
            continue
        out.write_bytes(path.read_bytes())


if __name__ == '__main__':
    TODAY = date.today().strftime("%Y-%m-%d")
    main(outdir=Path(f"~/Downloads/standalone-notes-backup--{TODAY}"))