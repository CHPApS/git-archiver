import os
import time
import logging
import gitlab
from typing import Dict, Any, List
from .base_archiver import BaseArchiver


class GitLabArchiver(BaseArchiver):
    """
    GitLab-specific archiver that extends BaseArchiver with GitLab API functionality.
    """
    
    def __init__(self, access_token: str, gitlab_url: str = "https://gitlab.com"):
        """
        Initialize the GitLab archiver.
        
        Args:
            access_token: GitLab API token with appropriate scopes
            gitlab_url: GitLab instance URL (default: https://gitlab.com)
        """
        super().__init__("gitlab")
        self.access_token = access_token
        self.gitlab_url = gitlab_url
        self.gl: gitlab.Gitlab = None  # type: ignore
        self._authenticated = False
    
    def _ensure_authenticated(self):
        """Ensure GitLab client is authenticated."""
        if not self._authenticated:
            self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.access_token)
            self.gl.auth()
            self._authenticated = True
    
    def recurse_groups_for_projects(self, group_id) -> List[Dict[str, Any]]:
        """
        Recursively get all projects from a group and its subgroups.
        
        Args:
            group_id: GitLab group ID or name
            
        Returns:
            List of project information dictionaries
        """
        self._ensure_authenticated()
        group = self.gl.groups.get(group_id)
        projects = []
        
        self.log.info(f"  Fetching groups for group: {group.attributes['full_name']}")
        subgroups = group.subgroups.list(all=True)
        
        if len(subgroups) > 0:
            for subgroup in subgroups:
                subgroup_id = subgroup.get_id()
                if subgroup_id is not None:
                    projects += self.recurse_groups_for_projects(subgroup_id)
        
        group_projects = group.projects.list(get_all=True)
        
        projects += [
            {
                "name": self._sanitize_name(p.attributes["name"]),
                "name_with_namespace": self._sanitize_name(p.attributes["name_with_namespace"]),
                "id": p.attributes["id"],
            }
            for p in group_projects
        ]
        
        return projects
    
    def get_repositories(self) -> List[Dict[str, Any]]:
        """
        Get a list of repositories from the GitLab group.
        This method is required by the base class but not used directly in GitLab workflow.
        
        Returns:
            List of repository information dictionaries
        """
        # This method is implemented for base class compatibility
        # but GitLab archiver uses recurse_groups_for_projects instead
        return []
    
    def download_export(self, repo_info: Dict[str, Any], file_path: str) -> None:
        """
        Download the export archive for a repository.
        
        Args:
            repo_info: Repository information dictionary
            file_path: Directory path where the export should be saved
        """
        self._ensure_authenticated()
        project_id = repo_info["id"]
        project = self.gl.projects.get(project_id)
        
        self.log.info("  Triggering export...")
        export = project.exports.create({})  # Sends an email to the token owner
        
        # Wait for the operation to finish
        server_ready = False
        while not server_ready:
            try:
                export.refresh()
                server_ready = True
            except Exception as e:
                self.log.error(f"Error refreshing export status: {e}")
                server_ready = False
        
        # Check export status
        self.log.info(f"  Export status: {export.export_status}")
        while export.export_status != "finished":
            time.sleep(1)
            export.refresh()
            self.log.info(f"  Export status: {export.export_status}")
        
        # Generate standardized filename using base class method
        gitlab_version = self.gl.version()[0]
        file_name = self.generate_export_filename(repo_info, version=gitlab_version, extension="tgz")
        full_path = os.path.join(file_path, file_name)
        
        # Download the export
        self.log.info("  Downloading and saving export...")
        try:
            with open(full_path, "wb") as f:
                export.download(streamed=True, action=f.write)
        except Exception as e:
            self.log.error(f"Error downloading export: {e}")
            self.log.error("  Download of export failed!")
    
    def download_repository_archive(self, repo_info: Dict[str, Any], file_path: str, ref: str = "") -> None:
        """
        Download the repository archive for a repository.
        
        Args:
            repo_info: Repository information dictionary
            file_path: Directory path where the archive should be saved
            ref: Reference (branch, tag, commit) to archive (not used in GitLab implementation)
        """
        self._ensure_authenticated()
        project_id = repo_info["id"]
        project = self.gl.projects.get(project_id)
        
        # Get the latest commit SHA
        commits = project.commits.list(per_page=1, get_all=False)
        sha = commits[0].attributes["id"] if len(commits) > 0 else "null"
        
        # Generate standardized filename using base class method
        file_name = self.generate_repository_archive_filename(repo_info, sha, extension="tgz")
        full_path = os.path.join(file_path, file_name)
        
        # Download the archive
        self.log.info(f"  Downloading and saving repository archive (SHA: {sha})...")
        try:
            tgz = project.repository_archive()
            with open(full_path, "wb") as f:
                f.write(tgz)
        except Exception as e:
            self.log.error(f"Error downloading repository archive: {e}")
            self.log.error("  Download of repository archive failed!")


def main(config=None, args=None):
    """Main function to run the GitLab archiver."""
    from .config import ConfigManager
    import argparse
    
    # Use provided config or create new one
    if config is None:
        config = ConfigManager()
    
    log = logging.getLogger()
    
    # Get GitLab configuration
    gitlab_config = config.get_section('gitlab')
    access_token = gitlab_config.get('api_token')
    gitlab_url = gitlab_config.get('gitlab_url', 'https://gitlab.com')
    group_id = gitlab_config.get('group_id')
    repositories = gitlab_config.get('repositories')
    export_path = gitlab_config.get('export_path', 'exports/gitlab')
    
    if not access_token or not group_id:
        log.error("GitLab API token and group ID are required")
        log.error("Set them in config.json, environment variables, or command line arguments")
        return
    
    # Parse repository filter
    repo_filter = None
    if repositories:
        repositories = repositories.strip().replace(",", " ").replace(";", " ")
        repo_filter = [r for r in repositories.split() if r]
        if repo_filter:
            log.info(f"Filtering by repositories: {repo_filter}")
    
    # Check for dry run
    dry_run = getattr(args, 'dry_run', False) if args else False
    if dry_run:
        log.info("DRY RUN MODE - No actual operations will be performed")
    
    # Initialize archiver
    archiver = GitLabArchiver(access_token, gitlab_url)
    
    log.info("-" * 80)
    log.info(f"Authenticating to GitLab at {gitlab_url}...")
    
    if dry_run:
        log.info("Would authenticate and fetch projects...")
        return
    
    log.info("-" * 80)
    log.info(f"Starting export of projects in group {group_id}")
    log.info("Recursing groups to get projects: ")
    projects = archiver.recurse_groups_for_projects(group_id)
    
    log.info("-" * 80)
    log.info("Projects found: ")
    for project in projects:
        print(f"  {project['name_with_namespace']} ({project['id']})")
    
    log.info("-" * 80)
    i = 0
    total = len(projects)
    digits = len(str(total))
    
    for project in projects:
        i += 1
        
        # Log progress
        log.info(f"Project {str(i).zfill(digits)}/{str(total)}")
        
        # Filter repositories
        if repo_filter:
            repo_in_filter = (str(project["name"]) in repo_filter) or (str(project["id"]) in repo_filter)
            if not repo_in_filter:
                log.info(f"Skipping {project['name']} - not in filter")
                continue
        
        log.info(f"Processing {project['name']} ({project['name_with_namespace']} - {project['id']})")
        
        # Create directory using configured export path
        project_path = os.path.join(export_path, project['name_with_namespace'])
        archiver.ensure_directory_exists(project_path)
        log.info(f"  Exporting to {project_path}")
        
        # Download export and repository archive
        try:
            archiver.download_export(project, project_path)
            archiver.download_repository_archive(project, project_path)
        except Exception as e:
            log.error(f"Error processing {project['name']}: {e}")
        
        # Add delay between projects if configured
        retry_delay = gitlab_config.get('retry_delay', 1)
        if retry_delay > 0:
            time.sleep(retry_delay)
    
    log.info("Done!")


if __name__ == "__main__":
    main()
