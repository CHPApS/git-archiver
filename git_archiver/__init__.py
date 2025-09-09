"""
Git Archiver Package

A package for archiving repositories from various Git platforms (GitHub, GitLab)
with standardized naming conventions, configuration management, and common functionality.
"""

from .base_archiver import BaseArchiver
from .github_archiver import GitHubArchiver
from .config import ConfigManager

# Optional GitLab import
try:
    from .gitlab_archiver import GitLabArchiver
    GITLAB_AVAILABLE = True
    __all__ = ["BaseArchiver", "GitHubArchiver", "GitLabArchiver", "ConfigManager"]
except ImportError:
    GITLAB_AVAILABLE = False
    __all__ = ["BaseArchiver", "GitHubArchiver", "ConfigManager"]

__version__ = "1.0.0"