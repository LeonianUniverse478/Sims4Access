"""Rewrite the source path baked into every .pyc inside a .ts4script to the bare file name.

PyZipFile records the path it was given as co_filename, so a build from an absolute
root ships the machine's full directory layout in every code object. Run under the
same Python the game uses (3.7) so the marshal format stays valid.

    py -3.7 tools/vendor/strip_pyc_paths.py path/to/mod.ts4script [more.ts4script ...]

The archive is rewritten in place (via a temp file); entry order, names and the
16-byte pyc headers are kept.
"""
import marshal
import os
import sys
import types
import zipfile


def _strip(code, filename):
    consts = tuple(_strip(c, filename) if isinstance(c, types.CodeType) else c for c in code.co_consts)
    return types.CodeType(
        code.co_argcount, code.co_kwonlyargcount, code.co_nlocals, code.co_stacksize,
        code.co_flags, code.co_code, consts, code.co_names, code.co_varnames, filename,
        code.co_name, code.co_firstlineno, code.co_lnotab, code.co_freevars, code.co_cellvars)


def strip_archive(path):
    tmp = path + '.tmp'
    changed = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as zout:
        for info in zin.infolist():
            data = zin.read(info)
            if info.filename.lower().endswith('.pyc'):
                header, body = data[:16], data[16:]
                code = marshal.loads(body)
                bare = os.path.basename(code.co_filename.replace('\\', '/'))
                if code.co_filename != bare:
                    code = _strip(code, bare)
                    data = header + marshal.dumps(code)
                    changed += 1
            zout.writestr(info, data)
    os.replace(tmp, path)
    return changed


def main(argv):
    if sys.version_info[:2] != (3, 7):
        print('run this under Python 3.7 (py -3.7), the game\'s bytecode version')
        return 2
    if not argv:
        print(__doc__)
        return 1
    for path in argv:
        n = strip_archive(path)
        print('{}: {} module(s) rewritten'.format(path, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
