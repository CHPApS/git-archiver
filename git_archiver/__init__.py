"""
Git Archiver Package

A package for archiving repositories from various Git platforms (GitHub, GitLab)
with standardized naming conventions and common functionality.
"""

from .base_archiver import BaseArchiver
from .github_archiver import GitHubArchiver
from .gitlab_archiver import GitLabArchiver

__version__ = "0.2.0"
__all__ = ["BaseArchiver", "GitHubArchiver", "GitLabArchiver"]