"""Compile and package the mod into a .ts4script, then install it.

The game only ever imports .pyc from a .ts4script - a .py in the archive is
enumerated and then silently skipped - so every module has to be compiled with
a real Python 3.7 before packaging. Sources are shipped alongside anyway, for
anyone who wants to read what the mod is doing.

Run with the bundled py37 interpreter:
    py37\\python.exe tools\\package.py
"""
import compileall
import os
import py_compile
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, 'build')
ARCHIVE = os.path.join(BUILD, 'Sims4Access.ts4script')
MODS = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Documents',
                    'Electronic Arts', 'The Sims 4', 'Mods')
DATA_FILES = ('a11yscan_names.bin', 'a11yscan_objects.bin')
# Nothing loose of our own any more: speech is Prism, which lives in
# native/ and is installed through NATIVE_FILES below.
LOOSE_FILES = ()
# Prebuilt Prism libraries, shipped alongside the mod so nobody has to build a
# C++ project to hear the game. Prism has no official binaries, so these come
# from our own build. Whatever is present in native/ gets installed; missing
# platforms are simply skipped.
NATIVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'native')
NATIVE_FILES = ('prism.dll', 'libprism.dylib', 'libprism.so')
MIRROR = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Documents',
                      'Sims4ScannerTools', 'src')

if sys.version_info[:2] != (3, 7):
    raise SystemExit('must run under Python 3.7, not %d.%d' % sys.version_info[:2])


def sources():
    return sorted(name for name in os.listdir(BUILD)
                  if name.startswith('a11yscan_') and name.endswith('.py'))


def compile_all():
    """Compile each module beside its source, failing loudly on a syntax error."""
    compiled = []
    for name in sources():
        src = os.path.join(BUILD, name)
        dst = os.path.join(BUILD, name[:-3] + '.pyc')
        py_compile.compile(src, cfile=dst, doraise=True)
        compiled.append(os.path.basename(dst))
        print('  compiled', name)
    return compiled


def package(compiled):
    with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in compiled:
            archive.write(os.path.join(BUILD, name), name)
        for name in sources():
            archive.write(os.path.join(BUILD, name), name)
        ctypes_dir = os.path.join(BUILD, 'ctypes')
        for root, _dirs, files in os.walk(ctypes_dir):
            for name in files:
                if not name.endswith('.pyc'):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, BUILD).replace('\\', '/')
                archive.write(full, rel)
        for name in DATA_FILES:
            full = os.path.join(BUILD, name)
            if os.path.exists(full):
                archive.write(full, name)
    print('  packaged %s (%.1f MB)' % (os.path.basename(ARCHIVE),
                                       os.path.getsize(ARCHIVE) / 1e6))


def install():
    if not os.path.isdir(MODS):
        print('  Mods folder not found, skipping install:', MODS)
        return
    for name in [os.path.basename(ARCHIVE)] + list(DATA_FILES + LOOSE_FILES
                                                  + NATIVE_FILES):
        if name.endswith('.ts4script'):
            source = ARCHIVE
        elif name in NATIVE_FILES:
            source = os.path.join(NATIVE_DIR, name)
        else:
            source = os.path.join(BUILD, name)
        if not os.path.exists(source):
            continue
        try:
            shutil.copy2(source, os.path.join(MODS, name))
        except PermissionError:
            # The game holds the NVDA client DLL open while it is running. It
            # never changes between builds, so a locked copy is not a failure.
            print('  skipped (in use, unchanged):', name)
    print('  installed to', MODS)


def mirror():
    """Keep a readable copy of the sources outside the scratch directory."""
    if not os.path.isdir(os.path.dirname(MIRROR)):
        return
    if not os.path.isdir(MIRROR):
        os.makedirs(MIRROR)
    for name in sources():
        shutil.copy2(os.path.join(BUILD, name), os.path.join(MIRROR, name))
    print('  mirrored sources to', MIRROR)


if __name__ == '__main__':
    print('compiling...')
    compiled = compile_all()
    print('packaging...')
    package(compiled)
    install()
    mirror()
    print('done.')
