from __future__ import annotations

class ToolSecurityError(Exception):
    """Base pour les exceptions de sécurité des outils."""

class FileSecurityError(ToolSecurityError):
    """Violation de sécurité liée au système de fichiers."""

class ProcessSecurityError(ToolSecurityError):
    """Violation de sécurité liée à l'exécution de processus."""

class ShellSecurityError(ProcessSecurityError):
    """Compat pour les tests existants."""
