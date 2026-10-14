"""Copy the public development source into a folder (the repository's dev branch).

    py -3.7 tools/export_public_source.py <repository folder>

Copies the source set (source_exchange.allowed), the pinned reference inputs
that may be shared, and the speech pack, and leaves out what may not be
published or is private:
  - EA's interface movies (flash/work-*/gfx) and UI Cheats Extension's movies
    (flash/uicheats-base/*.swf): contributors make them with Dev.ps1 setup;
  - build output, dist, exchange, logs, dev.local.json and compiled files.
Files already in the destination that are no longer exported are removed
(.git and the repository's own top-level files listed in KEEP are kept). It
stops if a private path or address appears in any exported text.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from source_exchange import allowed  # noqa: E402

EXTRA_DIRS = ['reference', 'prism']
EXTRA_FILES = ['flash/uicheats-base/SOURCE.txt', 'flash/work-1.128.90/SOURCE.txt', 'release-assets/INSTALL FIRST.txt']
# The repository's own files on the dev branch, written by hand, not exported.
KEEP = {'.git', '.gitattributes', 'README.md', 'CONTRIBUTING.md', 'CONTRIBUTORS.md', 'LICENSE', '.github'}
TEXT = {'.py', '.md', '.txt', '.json', '.ps1', '.as', '.js', '.java', '.cs', '.tsv', '.cfg', '.ini'}
PATHS = r'(?i)\\users\\(?!<|you|name|public)[a-z0-9._-]+|/users/(?!<|you|name|public)[a-z0-9._-]+|/[a-z]/user[s]/'


def private_pattern():
    """Profile paths, plus the maintainer's own words: the Windows user name,
    the git email, and any lines of .private-words in the kit (never exported)."""
    words = [os.environ.get('USERNAME', '')]
    try:
        words.append(subprocess.run(['git', 'config', '--global', 'user.email'], stdout=subprocess.PIPE,
                                    universal_newlines=True).stdout.strip())
    except OSError:
        pass
    extra = ROOT / '.private-words'
    if extra.is_file():
        words += extra.read_text(encoding='utf-8').splitlines()
    words = [re.escape(w.strip()) for w in words if len(w.strip()) >= 4]
    return re.compile(PATHS + ''.join('|' + w for w in words), re.I)


def exported():
    files = []
    for top in ['Scripts', 'tools', 'docs', 'helper', 'flash']:
        for p in (ROOT / top).rglob('*'):
            name = p.relative_to(ROOT).as_posix()
            if p.is_file() and allowed(name):
                files.append(name)
    for name in ['compile.py', 'Dev.ps1', 'START-HERE.md', 'CLAUDE.md', 'README.txt', 'CONTROLS.txt',
                 'CHEATS.txt', 'README-SpeechPack.txt', 'dev.local.example.json']:
        if (ROOT / name).is_file():
            files.append(name)
    for top in EXTRA_DIRS:
        files += [p.relative_to(ROOT).as_posix() for p in (ROOT / top).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts]
    files += [n for n in EXTRA_FILES if (ROOT / n).is_file()]
    return sorted(set(files))


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: py -3.7 tools/export_public_source.py <repository folder>')
    dest = Path(sys.argv[1]).resolve()
    if not (dest / '.git').exists():
        sys.exit('The destination must be a git checkout of the dev branch.')
    files = exported()
    problems = []
    PRIVATE = private_pattern()
    for name in files:
        p = ROOT / name
        if p.suffix.lower() in TEXT:
            text = p.read_text(encoding='utf-8', errors='replace')
            for m in PRIVATE.finditer(text):
                problems.append(name + ': ' + text[max(0, m.start() - 30):m.end() + 10].replace('\n', ' '))
    if problems:
        sys.exit('Private paths or addresses found; fix them before exporting:\n' + '\n'.join(problems[:40]))
    for child in dest.iterdir():
        if child.name not in KEEP:
            shutil.rmtree(str(child)) if child.is_dir() else child.unlink()
    for name in files:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(ROOT / name), str(target))
    (dest / '.gitignore').write_text(
        '# Made locally by Dev.ps1 setup from your own installs; never commit them.\n'
        'flash/work-*/gfx/\nflash/work-compat/\nflash/uicheats-base/*.swf\n'
        '# Build output and private settings.\nbuild/\ndist/\nexchange/\n.handoff/\ndev.local.json\n'
        '__pycache__/\n*.pyc\n*.log\nhelper/*.exe\n', encoding='utf-8')
    # The build checks pinned files by hash, so git must keep every byte
    # (no line-ending conversion on any checkout).
    (dest / '.gitattributes').write_text('* -text\n', encoding='utf-8')
    print('Exported %d files to %s' % (len(files), dest))


if __name__ == '__main__':
    main()
