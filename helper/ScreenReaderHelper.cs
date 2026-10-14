// Standalone Windows UI. The options editor is embedded, never extracted or downloaded.
using System;
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

[assembly: AssemblyTitle("TS4 Access Helper")]
[assembly: AssemblyProduct("TS4 Access")]
[assembly: AssemblyDescription("Enable Sims 4 custom content and script mods")]
[assembly: AssemblyVersion("1.1.0.0")]
[assembly: AssemblyFileVersion("1.1.0.0")]

internal static class Program {
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
            return RunHelper(args);
        } catch (Exception e) {
            MessageBox.Show(e.Message, "TS4 Access helper could not start",
                            MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static int RunHelper(string[] args) {
        string userFolder = null;
        string statusFile = null;
        for (int i = 0; i < args.Length; i++) {
            if (args[i] == "--user-folder" && i + 1 < args.Length) userFolder = args[++i];
            else if (args[i] == "--status-file" && i + 1 < args.Length) statusFile = args[++i];
            else throw new ArgumentException("Unknown or incomplete helper argument: " + args[i]);
        }
        using (HelperBackend backend = new HelperBackend()) {
            if (userFolder == null) userFolder = backend.FindUserFolder();
            if (statusFile != null) {
                // Read-only diagnostic path: never enables mods or opens the game.
                File.WriteAllText(statusFile, backend.StatusJson(userFolder));
                return 0;
            }
            using (HelperWindow window = new HelperWindow(backend, userFolder)) Application.Run(window);
        }
        return 0;
    }
}

internal sealed class HelperBackend : IDisposable {
    private readonly Runspace runspace;
    internal HelperBackend() {
        InitialSessionState state = InitialSessionState.CreateDefault();
        runspace = RunspaceFactory.CreateRunspace(state);
        runspace.ApartmentState = ApartmentState.STA;
        runspace.ThreadOptions = PSThreadOptions.UseCurrentThread;
        runspace.Open();
        using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("TS4Access.Core.ps1"))
        using (StreamReader reader = new StreamReader(source))
        using (PowerShell shell = PowerShell.Create()) {
            shell.Runspace = runspace;
            shell.AddScript("$ErrorActionPreference = 'Stop'\n" + reader.ReadToEnd(), false);
            shell.Invoke();
            CheckErrors(shell);
        }
    }
    private static void CheckErrors(PowerShell shell) {
        if (shell.HadErrors) throw new InvalidOperationException(shell.Streams.Error[0].ToString());
    }
    private Collection<PSObject> Invoke(string command, string key, string value, bool json) {
        using (PowerShell shell = PowerShell.Create()) {
            shell.Runspace = runspace;
            shell.AddCommand(command).AddParameter(key, value);
            if (json) shell.AddCommand("ConvertTo-Json").AddParameter("Compress", true);
            Collection<PSObject> result = shell.Invoke();
            CheckErrors(shell);
            return result;
        }
    }
    internal string FindUserFolder() {
        Collection<PSObject> result = Invoke("Find-HelperUserFolder", "StartFolder", AppDomain.CurrentDomain.BaseDirectory, false);
        return result.Count == 0 ? null : result[0].ToString();
    }
    internal PSObject Status(string folder) { return Invoke("Get-HelperStatus", "UserFolder", folder, false)[0]; }
    internal string StatusJson(string folder) { return Invoke("Get-HelperStatus", "UserFolder", folder, true)[0].ToString(); }
    internal bool Enable(string folder) { return (bool)Invoke("Enable-HelperMods", "UserFolder", folder, false)[0].Properties["Changed"].Value; }
    public void Dispose() { runspace.Dispose(); }
}

internal sealed class HelperWindow : Form {
    private readonly HelperBackend backend;
    private string userFolder;
    private readonly Label status;
    private readonly Button enable;
    private readonly LinkLabel choose;
    private readonly ToolTip folderTip = new ToolTip();
    private readonly Color ink = Color.FromArgb(30, 38, 49);
    private readonly Color accent = Color.FromArgb(31, 86, 179);

    internal HelperWindow(HelperBackend backend, string userFolder) {
        this.backend = backend;
        this.userFolder = userFolder;
        Text = "TS4 Access Helper";
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
        title.Text = "TS4 Access";
        title.Font = new Font("Segoe UI", 24F, FontStyle.Bold);
        title.AutoSize = true;
        title.Margin = new Padding(0, 0, 0, 8);
        layout.Controls.Add(title, 0, 0);

        Label introduction = new Label();
        introduction.Text = "Close The Sims 4 before enabling mods.";
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

        enable = new Button();
        enable.Text = "&Enable Script Mods";
        enable.AccessibleName = "Enable Script Mods";
        enable.Dock = DockStyle.Fill;
        enable.Margin = new Padding(0);
        enable.TabIndex = 0;
        enable.Font = new Font(Font, FontStyle.Bold);
        if (!SystemInformation.HighContrast) {
            enable.FlatStyle = FlatStyle.Flat;
            enable.FlatAppearance.BorderSize = 1;
            enable.BackColor = accent;
            enable.ForeColor = Color.White;
        }
        enable.Click += EnableMods;
        layout.Controls.Add(enable, 0, 3);

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
        AcceptButton = enable;
        RefreshStatus();
        Shown += delegate { if (enable.Enabled) enable.Focus(); else choose.Focus(); };
    }

    private void SetStatus(string text, bool success) {
        status.Text = text;
        status.AccessibleName = text;
        status.ForeColor = SystemInformation.HighContrast ? SystemColors.WindowText :
                           (success ? Color.FromArgb(28, 104, 59) : ink);
    }

    private void RefreshStatus() {
        PSObject state = backend.Status(userFolder);
        bool found = (bool)state.Properties["OptionsFound"].Value;
        string error = Convert.ToString(state.Properties["Error"].Value);
        bool enabled = (bool)state.Properties["ModsEnabled"].Value;
        enable.Enabled = found && String.IsNullOrEmpty(error);
        enable.AccessibleDescription = "Enables custom content and script mods. " +
            (found ? "Sims folder: " + userFolder : "Choose your Sims folder first.");
        folderTip.SetToolTip(choose, found ? userFolder : "Select Options.ini in your Sims 4 user folder.");
        choose.AccessibleDescription = folderTip.GetToolTip(choose);
        if (!found) SetStatus("Choose your Sims folder to continue.", false);
        else if (!String.IsNullOrEmpty(error)) SetStatus(error, false);
        else SetStatus(enabled ? "Script mods are enabled." : "Script mods are off.", enabled);
    }

    private void EnableMods(object sender, EventArgs e) {
        enable.Enabled = false;
        UseWaitCursor = true;
        try {
            bool changed = backend.Enable(userFolder);
            string message = changed ? "Script mods are enabled." : "Script mods are already enabled.";
            SetStatus(message, true);
            UseWaitCursor = false;
            // Standard focused dialog announces completion through the user's screen reader.
            MessageBox.Show(this, message + "\nYou can now open The Sims 4.", "TS4 Access",
                            MessageBoxButtons.OK, MessageBoxIcon.Information);
        } catch (Exception error) {
            SetStatus("Could not enable script mods. Try again after fixing the problem.", false);
            UseWaitCursor = false;
            MessageBox.Show(this, error.Message, "TS4 Access", MessageBoxButtons.OK, MessageBoxIcon.Error);
        } finally {
            UseWaitCursor = false;
            enable.Enabled = true;
            enable.Focus();
        }
    }

    private void ChooseFolder(object sender, LinkLabelLinkClickedEventArgs e) {
        using (OpenFileDialog dialog = new OpenFileDialog()) {
            dialog.Title = "Choose Options.ini in your Sims 4 user folder";
            dialog.Filter = "Sims 4 settings (Options.ini)|Options.ini";
            dialog.FileName = "Options.ini";
            dialog.CheckFileExists = true;
            dialog.Multiselect = false;
            dialog.InitialDirectory = Directory.Exists(userFolder) ? userFolder : Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
            if (dialog.ShowDialog(this) != DialogResult.OK) return;
            if (!String.Equals(Path.GetFileName(dialog.FileName), "Options.ini", StringComparison.OrdinalIgnoreCase)) {
                MessageBox.Show(this, "Choose the file named Options.ini.", "TS4 Access", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            userFolder = Path.GetDirectoryName(dialog.FileName);
            RefreshStatus();
            if (enable.Enabled) enable.Focus();
        }
    }

    protected override void Dispose(bool disposing) {
        if (disposing) folderTip.Dispose();
        base.Dispose(disposing);
    }
}
