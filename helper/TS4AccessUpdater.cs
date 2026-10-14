// TS4 Access Updater: installs the latest TS4 Access build from the project's
// GitHub releases. Standalone Windows UI like TS4AccessHelper; its logic is the
// embedded TS4AccessUpdater.Core.ps1 plus the helper's own core for finding the
// Sims folder and enabling script mods.
using System;
using System.Collections;
using System.Collections.ObjectModel;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using System.Management.Automation;
using System.Management.Automation.Runspaces;

[assembly: AssemblyTitle("TS4 Access Updater")]
[assembly: AssemblyProduct("TS4 Access")]
[assembly: AssemblyDescription("Install the latest TS4 Access build")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

internal static class Program {
    internal const string Repo = "LeonianUniverse478/Sims4Access";

    [DllImport("user32.dll")]
    private static extern bool SetProcessDPIAware();

    [STAThread]
    private static int Main(string[] args) {
        SetProcessDPIAware();
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        try {
            string psHome = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),
                                         @"WindowsPowerShell\v1.0");
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
                string name = new AssemblyName(e.Name).Name;
                if (name.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0) return null;
                string path = Path.Combine(psHome, name + ".dll");
                return File.Exists(path) ? Assembly.LoadFrom(path) : null;
            };
            Assembly.Load("System.Management.Automation, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35");
            return RunUpdater(args);
        } catch (Exception e) {
            MessageBox.Show(e.Message, "TS4 Access updater could not start",
                            MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static int RunUpdater(string[] args) {
        string userFolder = null;
        string package = null;
        for (int i = 0; i < args.Length; i++) {
            if (args[i] == "--user-folder" && i + 1 < args.Length) userFolder = args[++i];
            else if (args[i] == "--install-folder" && i + 1 < args.Length) package = args[++i];
            else throw new ArgumentException("Unknown or incomplete updater argument: " + args[i]);
        }
        using (UpdaterBackend backend = new UpdaterBackend()) {
            if (userFolder == null) userFolder = backend.FindUserFolder();
            if (package != null) {
                // Offline install of an unpacked package (used by the kit's tests).
                backend.InstallFolder(userFolder, package);
                return 0;
            }
            using (UpdaterWindow window = new UpdaterWindow(backend, userFolder)) Application.Run(window);
        }
        return 0;
    }
}

internal sealed class UpdaterBackend : IDisposable {
    private readonly Runspace runspace;
    internal UpdaterBackend() {
        runspace = RunspaceFactory.CreateRunspace(InitialSessionState.CreateDefault());
        runspace.ApartmentState = ApartmentState.STA;
        runspace.ThreadOptions = PSThreadOptions.UseCurrentThread;
        runspace.Open();
        foreach (string resource in new string[] { "TS4Access.Core.ps1", "TS4Access.Updater.ps1" }) {
            using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream(resource))
            using (StreamReader reader = new StreamReader(source))
            using (PowerShell shell = PowerShell.Create()) {
                shell.Runspace = runspace;
                shell.AddScript("$ErrorActionPreference = 'Stop'\n" + reader.ReadToEnd(), false);
                shell.Invoke();
                CheckErrors(shell);
            }
        }
    }
    private static void CheckErrors(PowerShell shell) {
        if (shell.HadErrors) throw new InvalidOperationException(shell.Streams.Error[0].ToString());
    }
    private Collection<PSObject> Invoke(string command, IDictionary parameters) {
        using (PowerShell shell = PowerShell.Create()) {
            shell.Runspace = runspace;
            shell.AddCommand(command).AddParameters(parameters);
            Collection<PSObject> result = shell.Invoke();
            CheckErrors(shell);
            return result;
        }
    }
    private static Hashtable Args(params object[] pairs) {
        Hashtable table = new Hashtable();
        for (int i = 0; i + 1 < pairs.Length; i += 2) table[pairs[i]] = pairs[i + 1];
        return table;
    }
    internal string FindUserFolder() {
        Collection<PSObject> result = Invoke("Find-HelperUserFolder", Args("StartFolder", AppDomain.CurrentDomain.BaseDirectory));
        return result.Count == 0 ? null : result[0].ToString();
    }
    internal PSObject Latest() { return Invoke("Get-UpdaterRelease", Args("Repo", Program.Repo))[0]; }
    internal string InstalledTag(string folder) {
        Collection<PSObject> result = Invoke("Get-UpdaterInstalledTag", Args("UserFolder", folder));
        return result.Count == 0 ? "" : result[0].ToString();
    }
    internal PSObject Update(string folder) { return Invoke("Update-TS4Access", Args("UserFolder", folder, "Repo", Program.Repo))[0]; }
    internal PSObject InstallFolder(string folder, string package) {
        return Invoke("Install-UpdaterPackage", Args("UserFolder", folder, "Package", package))[0];
    }
    public void Dispose() { runspace.Dispose(); }
}

internal sealed class UpdaterWindow : Form {
    private readonly UpdaterBackend backend;
    private string userFolder;
    private readonly Label status;
    private readonly Button update;
    private readonly LinkLabel choose;
    private readonly ToolTip folderTip = new ToolTip();
    private readonly Color ink = Color.FromArgb(30, 38, 49);
    private readonly Color accent = Color.FromArgb(31, 86, 179);

    internal UpdaterWindow(UpdaterBackend backend, string userFolder) {
        this.backend = backend;
        this.userFolder = userFolder;
        Text = "TS4 Access Updater";
        AccessibleName = Text;
        Font = new Font("Segoe UI", 11F);
        AutoScaleDimensions = new SizeF(96F, 96F);
        AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(560, 320);
        MinimumSize = new Size(480, 330);
        StartPosition = FormStartPosition.CenterScreen;
        MaximizeBox = false;
        BackColor = SystemInformation.HighContrast ? SystemColors.Window : Color.White;
        ForeColor = SystemInformation.HighContrast ? SystemColors.WindowText : ink;
        KeyPreview = true;
        KeyDown += delegate(object sender, KeyEventArgs e) {
            if (e.KeyCode == Keys.Escape) { e.Handled = true; Close(); }
            else if (e.Alt && e.KeyCode == Keys.F) { e.Handled = true; ChooseFolder(choose, null); }
        };

        TableLayoutPanel layout = new TableLayoutPanel();
        layout.Dock = DockStyle.Fill;
        layout.Padding = new Padding(28);
        layout.ColumnCount = 1;
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
        layout.RowCount = 5;
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 50F));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        Controls.Add(layout);

        Label title = new Label();
        title.Text = "TS4 Access Updater";
        title.Font = new Font("Segoe UI", 22F, FontStyle.Bold);
        title.AutoSize = true;
        title.Margin = new Padding(0, 0, 0, 8);
        layout.Controls.Add(title, 0, 0);

        Label introduction = new Label();
        introduction.Text = "Close The Sims 4, then press Enter to install the latest TS4 Access build.";
        introduction.AutoSize = true;
        introduction.Dock = DockStyle.Fill;
        introduction.Margin = new Padding(0, 0, 0, 12);
        layout.Controls.Add(introduction, 0, 1);

        status = new Label();
        status.Dock = DockStyle.Fill;
        status.TextAlign = ContentAlignment.MiddleLeft;
        status.AccessibleName = "Status";
        status.Margin = new Padding(0, 0, 0, 14);
        layout.Controls.Add(status, 0, 2);

        update = new Button();
        update.Text = "&Check for updates and install";
        update.AccessibleName = "Check for updates and install";
        update.Dock = DockStyle.Fill;
        update.Margin = new Padding(0);
        update.TabIndex = 0;
        update.Font = new Font(Font, FontStyle.Bold);
        if (!SystemInformation.HighContrast) {
            update.FlatStyle = FlatStyle.Flat;
            update.FlatAppearance.BorderSize = 1;
            update.BackColor = accent;
            update.ForeColor = Color.White;
        }
        update.Click += RunUpdate;
        layout.Controls.Add(update, 0, 3);

        choose = new LinkLabel();
        choose.Text = "Choose Sims folder...";
        choose.AccessibleName = "Choose Sims folder";
        choose.AutoSize = true;
        choose.Anchor = AnchorStyles.None;
        choose.Margin = new Padding(0, 16, 0, 0);
        choose.TabIndex = 1;
        choose.LinkColor = SystemInformation.HighContrast ? SystemColors.HotTrack : accent;
        choose.ActiveLinkColor = choose.LinkColor;
        choose.VisitedLinkColor = choose.LinkColor;
        choose.LinkClicked += ChooseFolder;
        layout.Controls.Add(choose, 0, 4);
        AcceptButton = update;
        RefreshStatus();
        Shown += delegate { if (update.Enabled) update.Focus(); else choose.Focus(); };
    }

    private bool FolderFound { get { return userFolder != null && File.Exists(Path.Combine(userFolder, "Options.ini")); } }

    private void SetStatus(string text) {
        status.Text = text;
        status.AccessibleName = text;
        status.Refresh();
    }

    private void RefreshStatus() {
        update.Enabled = FolderFound;
        folderTip.SetToolTip(choose, FolderFound ? userFolder : "Select Options.ini in your Sims 4 user folder.");
        choose.AccessibleDescription = folderTip.GetToolTip(choose);
        update.AccessibleDescription = FolderFound ? "Sims folder: " + userFolder : "Choose your Sims folder first.";
        if (!FolderFound) { SetStatus("Choose your Sims folder to continue."); return; }
        string installed = backend.InstalledTag(userFolder);
        SetStatus(installed == "" ? "Ready to install." : "Installed build: " + installed + ".");
    }

    private static string Describe(PSObject result) {
        string speech = Convert.ToString(result.Properties["SpeechPack"].Value);
        int extras = Convert.ToInt32(result.Properties["ExtraCopiesRemoved"].Value);
        string text = "TS4 Access " + Convert.ToString(result.Properties["Tag"].Value) + " is installed.";
        if (speech == "installed") text += "\nThe speech pack was installed.";
        if (extras > 0) text += "\nAn extra copy of the mod was moved to the backup so the game loads only one.";
        if (Convert.ToBoolean(result.Properties["ScriptModsChanged"].Value)) text += "\nScript mods were turned on.";
        text += "\nYou can now open The Sims 4.";
        return text;
    }

    private void RunUpdate(object sender, EventArgs e) {
        update.Enabled = false;
        UseWaitCursor = true;
        try {
            SetStatus("Checking GitHub for the latest build...");
            PSObject latest = backend.Latest();
            string tag = Convert.ToString(latest.Properties["Tag"].Value);
            string installed = backend.InstalledTag(userFolder);
            UseWaitCursor = false;
            if (installed == tag) {
                if (MessageBox.Show(this, "You already have the latest build, " + tag + ". Install it again anyway?", "TS4 Access",
                                    MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) != DialogResult.Yes) {
                    SetStatus("Up to date: " + tag + ".");
                    return;
                }
            }
            UseWaitCursor = true;
            long size = Convert.ToInt64(latest.Properties["Size"].Value);
            SetStatus("Downloading and installing " + tag + " (" + (size / 1048576) + " megabytes)...");
            PSObject result = backend.Update(userFolder);
            UseWaitCursor = false;
            string message = Describe(result);
            SetStatus("Installed build: " + tag + ".");
            MessageBox.Show(this, message, "TS4 Access", MessageBoxButtons.OK, MessageBoxIcon.Information);
        } catch (Exception error) {
            UseWaitCursor = false;
            SetStatus("The update did not finish.");
            MessageBox.Show(this, error.Message, "TS4 Access", MessageBoxButtons.OK, MessageBoxIcon.Error);
        } finally {
            UseWaitCursor = false;
            update.Enabled = FolderFound;
            if (update.Enabled) update.Focus();
        }
    }

    private void ChooseFolder(object sender, LinkLabelLinkClickedEventArgs e) {
        using (OpenFileDialog dialog = new OpenFileDialog()) {
            dialog.Title = "Choose Options.ini in your Sims 4 user folder";
            dialog.Filter = "Sims 4 settings (Options.ini)|Options.ini";
            dialog.FileName = "Options.ini";
            dialog.CheckFileExists = true;
            dialog.Multiselect = false;
            dialog.InitialDirectory = (userFolder != null && Directory.Exists(userFolder)) ? userFolder : Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
            if (dialog.ShowDialog(this) != DialogResult.OK) return;
            if (!String.Equals(Path.GetFileName(dialog.FileName), "Options.ini", StringComparison.OrdinalIgnoreCase)) {
                MessageBox.Show(this, "Choose the file named Options.ini.", "TS4 Access", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            userFolder = Path.GetDirectoryName(dialog.FileName);
            RefreshStatus();
            if (update.Enabled) update.Focus();
        }
    }

    protected override void Dispose(bool disposing) {
        if (disposing) folderTip.Dispose();
        base.Dispose(disposing);
    }
}
