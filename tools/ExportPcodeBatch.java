import java.io.*;
import java.nio.file.*;
import java.util.*;
import com.jpexs.decompiler.flash.SWF;
import com.jpexs.decompiler.flash.AbortRetryIgnoreHandler;
import com.jpexs.decompiler.flash.exporters.settings.ScriptExportSettings;
import com.jpexs.decompiler.flash.exporters.modes.ScriptExportMode;

/** Same FFDec pcode exporter as the CLI, retaining one JVM for the batch. */
public final class ExportPcodeBatch {
    public static void main(String[] args) throws Exception {
        var handler = new AbortRetryIgnoreHandler() {
            public int handle(Throwable error) {
                throw new RuntimeException("Pcode export failed", error);
            }
            public AbortRetryIgnoreHandler getNewInstance() { return this; }
        };
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            if (line.isBlank()) continue;
            String[] pair = line.split("\t", -1);
            if (pair.length != 2) throw new IOException("Invalid manifest line");
            Path input = Path.of(pair[0]), output = Path.of(pair[1]);
            if (Files.exists(output)) throw new IOException("Output already exists: " + output);
            try (InputStream stream = Files.newInputStream(input)) {
                SWF swf = new SWF(stream, false);
                var settings = new ScriptExportSettings(ScriptExportMode.PCODE, false, false, false, false);
                List<File> exported = swf.exportActionScript(handler, output.resolve("scripts").toString(), settings, true, null);
                if (exported.isEmpty() || exported.size() != swf.getAS3Packs().size()) {
                    throw new IOException("Incomplete script export: " + input);
                }
                for (File file : exported) {
                    if (!file.isFile() || file.length() == 0) throw new IOException("Missing export: " + file);
                }
                System.out.println("EXPORTED " + input.getFileName() + " " + exported.size());
            }
            System.gc();
        }
        // FFDec's worker pools retain non-daemon threads after export.
        System.exit(0);
    }
}
