import os
import shutil
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re


class ArchiveManager:
    """
    Manages archive rotation, retention policies, and disk space monitoring.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the archive manager.
        
        Args:
            config: Configuration dictionary containing retention settings
        """
        self.config = config
        self.log = logging.getLogger(__name__)
        
        # Get retention configuration
        retention_config = config.get('retention', {})
        self.max_archives_per_repo = retention_config.get('max_archives_per_repo', 5)
        self.max_age_days = retention_config.get('max_age_days', 30)
        self.min_free_space_gb = retention_config.get('min_free_space_gb', 10)
        self.cleanup_threshold_gb = retention_config.get('cleanup_threshold_gb', 5)
        self.enable_rotation = retention_config.get('enable_rotation', True)
        
        # Archive patterns for identification
        self.export_pattern = re.compile(r'export_(.+)_(\d+)(?:_(.+))?\.(tar\.gz|tgz)$')
        self.repo_pattern = re.compile(r'repository_archive_(.+)_(\d+)_([a-f0-9]+)\.(tar\.gz|tgz)$')
    
    def get_disk_usage(self, path: str) -> Tuple[float, float, float]:
        """
        Get disk usage statistics for a path.
        
        Args:
            path: Path to check
            
        Returns:
            Tuple of (total_gb, used_gb, free_gb)
        """
        try:
            stat = shutil.disk_usage(path)
            total_gb = stat.total / (1024**3)
            free_gb = stat.free / (1024**3)
            used_gb = total_gb - free_gb
            return total_gb, used_gb, free_gb
        except Exception as e:
            self.log.error(f"Failed to get disk usage for {path}: {e}")
            return 0.0, 0.0, 0.0
    
    def is_low_on_space(self, path: str) -> bool:
        """
        Check if the system is running low on disk space.
        
        Args:
            path: Path to check
            
        Returns:
            True if free space is below threshold
        """
        _, _, free_gb = self.get_disk_usage(path)
        return free_gb < self.min_free_space_gb
    
    def should_cleanup_aggressively(self, path: str) -> bool:
        """
        Check if aggressive cleanup is needed due to very low disk space.
        
        Args:
            path: Path to check
            
        Returns:
            True if aggressive cleanup is needed
        """
        _, _, free_gb = self.get_disk_usage(path)
        return free_gb < self.cleanup_threshold_gb
    
    def parse_archive_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Parse archive filename to extract metadata.
        
        Args:
            filename: Archive filename
            
        Returns:
            Dictionary with archive metadata or None if not recognized
        """
        # Try export pattern
        match = self.export_pattern.match(filename)
        if match:
            name, repo_id, version, extension = match.groups()
            return {
                'type': 'export',
                'name': name,
                'repo_id': int(repo_id),
                'version': version,
                'extension': extension,
                'filename': filename
            }
        
        # Try repository pattern
        match = self.repo_pattern.match(filename)
        if match:
            name, repo_id, sha, extension = match.groups()
            return {
                'type': 'repository',
                'name': name,
                'repo_id': int(repo_id),
                'sha': sha,
                'extension': extension,
                'filename': filename
            }
        
        return None
    
    def get_archive_age(self, filepath: str) -> float:
        """
        Get the age of an archive file in days.
        
        Args:
            filepath: Path to the archive file
            
        Returns:
            Age in days
        """
        try:
            mtime = os.path.getmtime(filepath)
            age_seconds = time.time() - mtime
            return age_seconds / (24 * 3600)  # Convert to days
        except Exception as e:
            self.log.error(f"Failed to get age for {filepath}: {e}")
            return 0.0
    
    def group_archives_by_repo(self, directory: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group archive files by repository.
        
        Args:
            directory: Directory to scan for archives
            
        Returns:
            Dictionary mapping repo keys to lists of archive info
        """
        archives_by_repo = {}
        
        if not os.path.exists(directory):
            return archives_by_repo
        
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if not os.path.isfile(filepath):
                continue
            
            archive_info = self.parse_archive_info(filename)
            if not archive_info:
                continue
            
            # Add file metadata
            archive_info['filepath'] = filepath
            archive_info['size_bytes'] = os.path.getsize(filepath)
            archive_info['age_days'] = self.get_archive_age(filepath)
            archive_info['mtime'] = os.path.getmtime(filepath)
            
            # Group by repository (name + id)
            repo_key = f"{archive_info['name']}_{archive_info['repo_id']}"
            if repo_key not in archives_by_repo:
                archives_by_repo[repo_key] = []
            
            archives_by_repo[repo_key].append(archive_info)
        
        # Sort archives by modification time (newest first)
        for repo_key in archives_by_repo:
            archives_by_repo[repo_key].sort(key=lambda x: x['mtime'], reverse=True)
        
        return archives_by_repo
    
    def identify_archives_for_removal(self, directory: str, aggressive: bool = False) -> List[str]:
        """
        Identify archives that should be removed based on retention policies.
        
        Args:
            directory: Directory to scan
            aggressive: If True, apply more aggressive cleanup
            
        Returns:
            List of file paths to remove
        """
        archives_by_repo = self.group_archives_by_repo(directory)
        files_to_remove = []
        
        for repo_key, archives in archives_by_repo.items():
            # Separate by type
            exports = [a for a in archives if a['type'] == 'export']
            repositories = [a for a in archives if a['type'] == 'repository']
            
            # Apply retention policies
            files_to_remove.extend(self._apply_retention_policy(exports, aggressive))
            files_to_remove.extend(self._apply_retention_policy(repositories, aggressive))
        
        return files_to_remove
    
    def _apply_retention_policy(self, archives: List[Dict[str, Any]], aggressive: bool = False) -> List[str]:
        """
        Apply retention policy to a list of archives.
        
        Args:
            archives: List of archive info dictionaries
            aggressive: If True, apply more aggressive cleanup
            
        Returns:
            List of file paths to remove
        """
        files_to_remove = []
        
        if not archives:
            return files_to_remove
        
        # Determine limits based on mode
        if aggressive:
            max_count = max(1, self.max_archives_per_repo // 2)  # Keep fewer archives
            max_age = max(7, self.max_age_days // 2)  # Shorter retention
        else:
            max_count = self.max_archives_per_repo
            max_age = self.max_age_days
        
        # Remove archives exceeding count limit (keep newest)
        if len(archives) > max_count:
            for archive in archives[max_count:]:
                files_to_remove.append(archive['filepath'])
                self.log.info(f"Marking for removal (count limit): {archive['filename']}")
        
        # Remove archives exceeding age limit
        for archive in archives:
            if archive['age_days'] > max_age:
                if archive['filepath'] not in files_to_remove:
                    files_to_remove.append(archive['filepath'])
                    self.log.info(f"Marking for removal (age limit): {archive['filename']} (age: {archive['age_days']:.1f} days)")
        
        return files_to_remove
    
    def cleanup_archives(self, directory: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Perform archive cleanup based on retention policies and disk space.
        
        Args:
            directory: Directory to clean up
            dry_run: If True, only simulate cleanup
            
        Returns:
            Dictionary with cleanup statistics
        """
        if not self.enable_rotation:
            self.log.info("Archive rotation is disabled")
            return {'removed_count': 0, 'freed_space_mb': 0, 'status': 'disabled'}
        
        self.log.info(f"Starting archive cleanup in {directory}")
        
        # Check disk space
        total_gb, used_gb, free_gb = self.get_disk_usage(directory)
        self.log.info(f"Disk usage: {used_gb:.1f}GB used, {free_gb:.1f}GB free of {total_gb:.1f}GB total")
        
        # Determine cleanup mode
        aggressive = self.should_cleanup_aggressively(directory)
        if aggressive:
            self.log.warning(f"Low disk space detected ({free_gb:.1f}GB free), applying aggressive cleanup")
        elif self.is_low_on_space(directory):
            self.log.warning(f"Disk space is getting low ({free_gb:.1f}GB free)")
        
        # Identify files to remove
        files_to_remove = self.identify_archives_for_removal(directory, aggressive)
        
        if not files_to_remove:
            self.log.info("No archives need to be removed")
            return {'removed_count': 0, 'freed_space_mb': 0, 'status': 'no_action_needed'}
        
        # Calculate space to be freed
        total_size_bytes = sum(os.path.getsize(f) for f in files_to_remove if os.path.exists(f))
        freed_space_mb = total_size_bytes / (1024 * 1024)
        
        self.log.info(f"Found {len(files_to_remove)} archives to remove, will free {freed_space_mb:.1f}MB")
        
        if dry_run:
            self.log.info("DRY RUN: Would remove the following files:")
            for filepath in files_to_remove:
                self.log.info(f"  - {os.path.basename(filepath)}")
            return {'removed_count': len(files_to_remove), 'freed_space_mb': freed_space_mb, 'status': 'dry_run'}
        
        # Remove files
        removed_count = 0
        actual_freed_bytes = 0
        
        for filepath in files_to_remove:
            try:
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    os.remove(filepath)
                    removed_count += 1
                    actual_freed_bytes += file_size
                    self.log.info(f"Removed: {os.path.basename(filepath)}")
                else:
                    self.log.warning(f"File not found: {filepath}")
            except Exception as e:
                self.log.error(f"Failed to remove {filepath}: {e}")
        
        actual_freed_mb = actual_freed_bytes / (1024 * 1024)
        self.log.info(f"Cleanup completed: removed {removed_count} files, freed {actual_freed_mb:.1f}MB")
        
        return {
            'removed_count': removed_count,
            'freed_space_mb': actual_freed_mb,
            'status': 'completed',
            'aggressive_mode': aggressive
        }
    
    def rotate_archives_before_download(self, directory: str, dry_run: bool = False) -> None:
        """
        Perform archive rotation before downloading new archives.
        
        Args:
            directory: Directory where archives will be stored
            dry_run: If True, only simulate rotation
        """
        if not self.enable_rotation:
            return
        
        self.log.info("Performing pre-download archive rotation")
        
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Check if cleanup is needed
        if self.is_low_on_space(directory):
            self.log.warning("Low disk space detected, performing cleanup before download")
            self.cleanup_archives(directory, dry_run)
        else:
            # Regular rotation based on count and age limits
            self.cleanup_archives(directory, dry_run)
    
    def get_retention_summary(self, directory: str) -> Dict[str, Any]:
        """
        Get a summary of current archive retention status.
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Dictionary with retention summary
        """
        archives_by_repo = self.group_archives_by_repo(directory)
        
        total_archives = sum(len(archives) for archives in archives_by_repo.values())
        total_size_bytes = 0
        oldest_archive_days = 0
        newest_archive_days = float('inf')
        
        repo_summaries = {}
        
        for repo_key, archives in archives_by_repo.items():
            repo_size = sum(a['size_bytes'] for a in archives)
            repo_oldest = max(a['age_days'] for a in archives) if archives else 0
            repo_newest = min(a['age_days'] for a in archives) if archives else 0
            
            total_size_bytes += repo_size
            oldest_archive_days = max(oldest_archive_days, repo_oldest)
            newest_archive_days = min(newest_archive_days, repo_newest)
            
            repo_summaries[repo_key] = {
                'count': len(archives),
                'size_mb': repo_size / (1024 * 1024),
                'oldest_days': repo_oldest,
                'newest_days': repo_newest
            }
        
        total_gb, used_gb, free_gb = self.get_disk_usage(directory)
        
        return {
            'total_archives': total_archives,
            'total_repositories': len(archives_by_repo),
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'oldest_archive_days': oldest_archive_days,
            'newest_archive_days': newest_archive_days if newest_archive_days != float('inf') else 0,
            'disk_usage': {
                'total_gb': total_gb,
                'used_gb': used_gb,
                'free_gb': free_gb,
                'low_space': self.is_low_on_space(directory)
            },
            'repositories': repo_summaries,
            'retention_config': {
                'max_archives_per_repo': self.max_archives_per_repo,
                'max_age_days': self.max_age_days,
                'min_free_space_gb': self.min_free_space_gb,
                'enable_rotation': self.enable_rotation
            }
        }