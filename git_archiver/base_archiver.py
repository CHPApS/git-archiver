import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseArchiver(ABC):
    """
    Base class for Git platform archivers that provides common archive naming structures
    and utility methods.
    """
    
    def __init__(self, platform_name: str):
        """
        Initialize the base archiver.
        
        Args:
            platform_name: Name of the platform (e.g., 'github', 'gitlab')
        """
        self.platform_name = platform_name.lower()
        self.log = logging.getLogger()
    
    def generate_export_filename(self, repo_info: Dict[str, Any], 
                                version: Optional[str] = None, 
                                extension: str = "tar.gz") -> str:
        """
        Generate a standardized filename for export archives.
        
        Args:
            repo_info: Dictionary containing repository information (name, id, etc.)
            version: Optional version string to include in filename
            extension: File extension (default: tar.gz)
            
        Returns:
            Standardized export filename
        """
        name = self._sanitize_name(repo_info.get('name', 'unknown'))
        repo_id = repo_info.get('id', 'unknown')
        
        if version:
            return f"export_{name}_{repo_id}_{version}.{extension}"
        else:
            return f"export_{name}_{repo_id}.{extension}"
    
    def generate_repository_archive_filename(self, repo_info: Dict[str, Any], 
                                           sha: str, 
                                           extension: str = "tar.gz") -> str:
        """
        Generate a standardized filename for repository archives.
        
        Args:
            repo_info: Dictionary containing repository information (name, id, etc.)
            sha: Commit SHA for the archive
            extension: File extension (default: tar.gz)
            
        Returns:
            Standardized repository archive filename
        """
        name = self._sanitize_name(repo_info.get('name', 'unknown'))
        repo_id = repo_info.get('id', 'unknown')
        
        return f"repository_archive_{name}_{repo_id}_{sha}.{extension}"
    
    def generate_export_path(self, base_path: str = "exports") -> str:
        """
        Generate the export directory path for this platform.
        
        Args:
            base_path: Base directory for exports (default: exports)
            
        Returns:
            Full path for platform exports
        """
        return os.path.join(base_path, self.platform_name)
    
    def ensure_directory_exists(self, directory_path: str) -> None:
        """
        Ensure that a directory exists, creating it if necessary.
        
        Args:
            directory_path: Path to the directory
        """
        os.makedirs(directory_path, exist_ok=True)
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize repository/project names for use in filenames.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name safe for use in filenames
        """
        # Remove spaces and other potentially problematic characters
        return name.replace(" ", "").replace("/", "_").replace("\\", "_")
    
    @abstractmethod
    def get_repositories(self) -> list:
        """
        Get a list of repositories from the platform.
        Must be implemented by subclasses.
        
        Returns:
            List of repository information dictionaries
        """
        pass
    
    @abstractmethod
    def download_export(self, repo_info: Dict[str, Any], file_path: str) -> None:
        """
        Download the export archive for a repository.
        Must be implemented by subclasses.
        
        Args:
            repo_info: Repository information dictionary
            file_path: Path where the export should be saved
        """
        pass
    
    @abstractmethod
    def download_repository_archive(self, repo_info: Dict[str, Any], 
                                  file_path: str, ref: str = "") -> None:
        """
        Download the repository archive for a repository.
        Must be implemented by subclasses.
        
        Args:
            repo_info: Repository information dictionary
            file_path: Path where the archive should be saved
            ref: Reference (branch, tag, commit) to archive
        """
        pass