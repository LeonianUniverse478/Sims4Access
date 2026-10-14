import java.io.*;
import java.nio.file.*;
import java.util.*;
import com.jpexs.decompiler.flash.SWF;
import com.jpexs.decompiler.flash.abc.ScriptPack;
import com.jpexs.decompiler.flash.importers.FFDecAs3ScriptReplacer;

/** Sequential FFDec replacements with a fresh SWF per manifest entry. */
public final class ReplaceScriptsBatch {
    public static void main(String[] args) throws Exception {
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            if (line.isBlank()) continue;
            String[] row = line.split("\t", -1);
            if (row.length < 4 || row.length % 2 != 0) throw new IOException("Invalid manifest line");
            Path input = Path.of(row[0]), output = Path.of(row[1]);
            if (Files.exists(output)) throw new IOException("Output already exists: " + output);
            try (InputStream stream = Files.newInputStream(input)) {
                SWF swf = new SWF(stream, false);
                for (int i = 2; i < row.length; i += 2) {
                    ScriptPack target = null;
                    for (ScriptPack pack : swf.getAS3Packs()) {
                        if (pack.getClassPath().toString().equals(row[i])) {
                            if (target != null) throw new IOException("Duplicate class: " + row[i]);
                            target = pack;
                        }
                    }
                    if (target == null) throw new IOException("Missing class: " + row[i]);
                    var replacer = new FFDecAs3ScriptReplacer(false);
                    if (!replacer.isAvailable()) throw new IOException("FFDec compiler unavailable");
                    if (!target.abc.replaceScriptPack(replacer, target,
                            Files.readString(Path.of(row[i + 1])), Collections.emptyList())) {
                        throw new IOException("Replacement failed: " + row[i]);
                    }
                }
                try (OutputStream dest = Files.newOutputStream(output, StandardOpenOption.CREATE_NEW)) {
                    swf.saveTo(dest);
                }
                System.out.println("REBUILT " + output.getFileName());
            }
            System.gc();
        }
        System.exit(0);
    }
}
