# Optional setup-helper test startup

The setup helper re-enables mods in Options.ini before game launch; it is not required by the running mod. Windows PowerShell on this machine also hangs on a print-only command, before the helper is loaded.

The Python launcher now probes startup for at most five seconds. Missing or unresponsive PowerShell reports an explicit optional-test skip (77), not a mod failure or a pass. Once PowerShell starts successfully, helper test failures and timeouts remain failures. The full report lists skipped and failed suites separately and does not mark incomplete coverage as fully passed. Six isolated launcher tests cover these outcomes. No helper behavior or installed game files changed.
