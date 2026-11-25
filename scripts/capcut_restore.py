"""List a project's backups, or put one back.

  python3 capcut_restore.py "project"                 list its backups, newest first
  python3 capcut_restore.py "project" BACKUP_NAME     restore that backup

Restoring backs up the project as it is now first, so a restore can be undone too.
Refuses while CapCut is open.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pdir = common.find_project(sys.argv[1])
    folder = common.HOME / "backups"
    backups = sorted((p for p in folder.glob(f"{pdir.name} *") if p.is_dir()), key=lambda p: p.name, reverse=True)
    if len(sys.argv) == 2:
        for b in backups[:30]:
            print(f"  {b.name}")
        print(f"{len(backups)} backups of {pdir.name} in {folder}")
        return
    b = folder / sys.argv[2]
    if b not in backups:
        sys.exit(f"No backup called {sys.argv[2]!r} for this project. Run without a name to list them.")
    safety = common.restore(pdir, b)
    print(f"Restored {b.name}. The state before the restore is saved as {safety.name}.")


if __name__ == "__main__":
    main()
