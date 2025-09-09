"""
Git Archiver Package

A package for archiving repositories from various Git platforms (GitHub, GitLab)
with standardized naming conventions, configuration management, and common functionality.
"""

from .base_archiver import BaseArchiver
from .github_archiver import GitHubArchiver
from .gitlab_archiver import GitLabArchiver
from .config import ConfigManager

__version__ = "1.0.0"
__all__ = ["BaseArchiver", "GitHubArchiver", "GitLabArchiver", "ConfigManager"]