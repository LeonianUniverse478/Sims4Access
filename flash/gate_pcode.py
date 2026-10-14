"""Bytecode fidelity gate for every movie build_ui_package.py ships (25).

rebuild_all.ps1 only checks that output starts with the bytes 'GFX', which a
semantically broken movie passes. The AS3 export also round-trips looking
identical while the bytecode differs, so reading the .as proves nothing either.
This compares actual opcodes against EA's originals.

Two assertions per movie:

  1. TARGETED classes (the ones we recompile) must not gain any generic
     increment/decrement/inclocal/declocal where EA used the _i integer form.
     A counter silently widening from int to Number is what crashed SimHub
     (2026-08-03, Vector index) and TimeControls.SetBlurPosition (patron crash
     on 1.126.78, getCharBoundaries index -> null deref -> native fault).

  2. UNTARGETED classes must be bytecode-identical. FFDec -replace should only
     rewrite what you name; anything else changing means collateral damage.

Usage: python gate_pcode.py <WorkDir>      (same -WorkDir as rebuild_all.ps1)
Exits non-zero and prints FAIL lines if the gate fails. Java, FFDec and the
batch helper folder come from flash_config (TS4_JAVA, TS4_FFDEC,
TS4_FFDEC_HELPERS).
"""
import ast
import collections
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import flash_config  # noqa: E402

TOOLTIP = "olympus.core.TooltipManager"
CELL = "widgets.BuildBuy.controls.CatalogImageCellView"
INT_OPS = ("increment", "inclocal", "decrement", "declocal")


def movie_list():
    src = open(os.path.join(HERE, "build_ui_package.py"), encoding="utf-8").read()
    body = re.sub(r"#.*", "", re.search(r"MOVIES\s*=\s*\{(.*?)\n\}", src, re.S).group(1))
    return sorted(ast.literal_eval("{" + body + "}"))


def extra_classes():
    """Per-movie extra targets from rebuild_all.ps1's $movies map."""
    src = open(os.path.join(HERE, "rebuild_all.ps1"), encoding="utf-8").read()
    m = re.search(r"\$movies\s*=\s*(?:\[ordered\])?\s*@\{(.*?)\n\}", src, re.S)
    if m is None:
        raise SystemExit("could not parse $movies out of rebuild_all.ps1")
    block = m.group(1)
    out = {}
    for line in block.splitlines():
        line = line.split("#")[0].strip()
        m = re.match(r"'([^']+)'\s*=\s*(.+)$", line)
        if not m:
            continue
        # the value holds alternating class name / .as path pairs; keep classes
        out[m.group(1)] = [q for q in re.findall(r'"([\w.]+\.[\w]+)"', m.group(2))
                           if not q.endswith(".as")]
    return out


def own_only():
    """Movies whose shared TooltipManager/CatalogImageCellView copies
    rebuild_all.ps1 leaves as EA shipped them ($ownOnly). Those copies are
    untargeted and must come through bytecode-identical."""
    src = open(os.path.join(HERE, "rebuild_all.ps1"), encoding="utf-8").read()
    m = re.search(r"^\s*\$ownOnly\s*=\s*\((.*)\)\s*$", src, re.M)
    names = re.findall(r"\$name\s+-eq\s+'([^']+)'", m.group(1)) if m else []
    if not names:
        raise SystemExit("could not parse $ownOnly out of rebuild_all.ps1")
    return set(names)


def export(swf, outdir):
    if os.path.isdir(outdir):
        return
    subprocess.run([flash_config.java(), "-jar", flash_config.ffdec(), "-format", "script:pcode",
                    "-export", "script", outdir, swf],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def export_many(pairs, work):
    """Use the same FFDec pcode exporter in one JVM for a large batch.

    The helper's 1,077 ClassLibraryGamedata pcode files were checked byte for
    byte against CLI export. All fidelity comparisons below are unchanged.
    """
    pending = [(os.path.abspath(swf), os.path.abspath(outdir))
               for swf, outdir in pairs if not os.path.isdir(outdir)]
    if not pending:
        return
    classes = os.path.abspath(flash_config.helpers())
    helper = os.path.join(classes, 'ExportPcodeBatch.class')
    if not os.path.isfile(helper):
        print('Exporting {} movies one JVM each (no ExportPcodeBatch.class in {})'.format(
            len(pending), classes), flush=True)
        for swf, outdir in pending:
            export(swf, outdir)
        return
    manifest = os.path.join(work, 'pcode-export-batch.tsv')
    with open(manifest, 'w', encoding='utf-8') as fh:
        for swf, outdir in pending:
            fh.write(swf + '\t' + outdir + '\n')
    print('Exporting {} movies with the FFDec batch exporter'.format(len(pending)), flush=True)
    log = os.path.join(work, 'pcode-export-batch.log')
    with open(log, 'w', encoding='utf-8') as fh:
        subprocess.run([flash_config.java(), '-Xmx2g', '-cp', classes + os.pathsep + flash_config.ffdec(),
                        'ExportPcodeBatch', manifest], stdout=fh, stderr=fh, check=True)


def scripts(root):
    base = os.path.join(root, "scripts")
    found = {}
    for dirpath, _dirs, files in os.walk(base):
        for fn in files:
            if fn.endswith(".pcode"):
                full = os.path.join(dirpath, fn)
                cls = os.path.relpath(full, base)[:-len(".pcode")].replace(os.sep, ".")
                found[cls] = full
    return found


def opcodes(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return collections.Counter(re.findall(r"^\s{6,}([a-z_0-9]+)", fh.read(), re.M))


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python gate_pcode.py <WorkDir>")
    work = sys.argv[1]
    gfx = os.path.join(work, "gfx")
    pc = os.path.join(work, "pcode")
    os.makedirs(pc, exist_ok=True)

    extras = extra_classes()
    shared_untouched = own_only()
    failed, checked = [], 0

    pairs = []
    for name in movie_list():
        for file_prefix, directory_prefix in (('ea_', 'ea_'), ('patched_', 'new_')):
            swf = os.path.join(gfx, file_prefix + name + '.swf')
            if os.path.isfile(swf):
                pairs.append((swf, os.path.join(pc, directory_prefix + name)))
    export_many(pairs, work)

    for name in movie_list():
        ea_swf = os.path.join(gfx, "ea_%s.swf" % name)
        new_swf = os.path.join(gfx, "patched_%s.swf" % name)
        if not (os.path.isfile(ea_swf) and os.path.isfile(new_swf)):
            failed.append("%s: missing ea_ or patched_ swf" % name)
            continue

        ea_txt = open(ea_swf, "rb").read()
        targeted = set(extras.get(name, []))
        if name not in shared_untouched and b"TooltipManager" in ea_txt:
            targeted.add(TOOLTIP)
        if name not in shared_untouched and b"CatalogImageCellView" in ea_txt:
            targeted.add(CELL)

        ea_dir, new_dir = os.path.join(pc, "ea_" + name), os.path.join(pc, "new_" + name)
        export(ea_swf, ea_dir)
        export(new_swf, new_dir)
        ea_s, new_s = scripts(ea_dir), scripts(new_dir)

        # 1. targeted classes must not degrade int ops
        for cls in sorted(targeted):
            if cls not in ea_s or cls not in new_s:
                failed.append("%s: targeted class %s not found in both" % (name, cls))
                continue
            a, b = opcodes(ea_s[cls]), opcodes(new_s[cls])
            checked += 1
            for op in INT_OPS:
                if b.get(op, 0) > a.get(op, 0):
                    failed.append("%s / %s: %s %d -> %d (EA used the _i integer form)"
                                  % (name, cls.split(".")[-1], op, a.get(op, 0), b.get(op, 0)))

        # 2. untargeted classes must be identical
        drifted = [c for c in sorted(set(ea_s) & set(new_s))
                   if c not in targeted and opcodes(ea_s[c]) != opcodes(new_s[c])]
        for c in drifted[:5]:
            failed.append("%s: untargeted class modified: %s" % (name, c))
        if len(drifted) > 5:
            failed.append("%s: ...and %d more untargeted classes modified"
                          % (name, len(drifted) - 5))

        gone = set(ea_s) - set(new_s)
        if gone:
            failed.append("%s: %d class(es) DISAPPEARED, e.g. %s"
                          % (name, len(gone), sorted(gone)[0]))

        print("  %-28s targeted=%-2d classes=%d" % (name, len(targeted), len(ea_s)))

    print("\n  targeted-class comparisons: %d" % checked)
    if failed:
        for line in failed:
            print("  FAIL " + line)
        sys.exit("\nfidelity gate FAILED; refusing to ship")
    print("  fidelity gate PASSED")


if __name__ == "__main__":
    main()
