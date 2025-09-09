import os
import logging
import time
import requests
import json
from typing import Dict, Any, Optional, List
from .base_archiver import BaseArchiver


class GitHubArchiver(BaseArchiver):
    """
    GitHub-specific archiver that extends BaseArchiver with GitHub API functionality.
    """
    
    def __init__(self, access_token: str, org_name: str):
        """
        Initialize the GitHub archiver.
        
        Args:
            access_token: GitHub API token with appropriate scopes
            org_name: GitHub organization name
        """
        super().__init__("github")
        self.access_token = access_token
        self.org_name = org_name
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
        }
    
    def get_repositories(self) -> List[Dict[str, Any]]:
        """
        Get a list of repositories under the organization.
        
        Returns:
            List of repository information dictionaries
        """
        self.log.info(f'Getting list of repos in organization "{self.org_name}"...')
        endpoint = f"https://api.github.com/orgs/{self.org_name}/repos"
        repos = []
        
        # Paginate through the results
        page = 1
        per_page = 100
        while True:
            self.log.info(f"  Getting page {page} (page size: {per_page}) of repos...")
            response = requests.get(
                endpoint, headers=self.headers, params={"per_page": per_page, "page": page}
            )
            
            if response.status_code != 200:
                self.log.error(
                    f"Error getting repositories: status code: {response.status_code}, text: {response.text}"
                )
                break
            
            response_obj = json.loads(response.text)
            repos.extend(response_obj)
            
            if len(response_obj) < per_page:
                break
            page += 1
        
        self.log.info(f"  Got {len(repos)} repos")
        return repos
    
    def create_migration_export(self, repo: Dict[str, Any]) -> Optional[int]:
        """
        Create a request for a migration archive for a repository.
        
        Args:
            repo: Repository information dictionary
            
        Returns:
            Migration ID if successful, None otherwise
        """
        self.log.info(f"Starting generation migration archive for {repo['name']}...")
        endpoint = f"https://api.github.com/orgs/{self.org_name}/migrations"
        
        data = {
            "lock_repositories": True,  # Must be manually unlocked!
            "lock_reason": "migrating",
            "repositories": [f"{self.org_name}/{repo['name']}"],
        }
        
        response = requests.post(endpoint, headers=self.headers, data=json.dumps(data))
        
        if response.status_code != 201:
            self.log.error(
                f"Error creating migration for {repo['name']}: status code: {response.status_code}, text: {response.text}"
            )
            return None
        
        response_obj = json.loads(response.text)
        migration_id = response_obj["id"]
        self.log.info(f"  Migration with migration_id={migration_id} created for {repo['name']}")
        return migration_id
    
    def get_migration_status(self, migration_id: int) -> Optional[str]:
        """
        Get the status of a migration.
        
        Args:
            migration_id: ID of the migration
            
        Returns:
            Migration status string if successful, None otherwise
        """
        self.log.info(f"Getting migration status for migration_id={migration_id}...")
        endpoint = f"https://api.github.com/orgs/{self.org_name}/migrations/{migration_id}"
        
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code != 200:
            self.log.error(
                f"Error getting migration status for migration_id={migration_id}: status code: {response.status_code}, text: {response.text}"
            )
            return None
        
        response_obj = json.loads(response.text)
        migration_status = response_obj["state"]
        self.log.info(f"  Migration status for migration_id={migration_id} is {migration_status}")
        return migration_status
    
    def unlock_repository(self, repo: Dict[str, Any]) -> None:
        """
        Unlock a repository after migration.
        
        Args:
            repo: Repository information dictionary with migration_id
        """
        self.log.info(f"Unlocking {repo['name']}...")
        endpoint = f"https://api.github.com/orgs/{self.org_name}/migrations/{repo['migration_id']}/repos/{repo['name']}/lock"
        
        response = requests.delete(endpoint, headers=self.headers)
        
        if response.status_code != 204:
            self.log.error(
                f"Error unlocking {repo['name']}: status code: {response.status_code}, text: {response.text}"
            )
            return
        
        self.log.info(f"  Successfully unlocked {repo['name']}")
    
    def get_commit_sha(self, repo: Dict[str, Any], ref: str = "") -> Optional[str]:
        """
        Get the commit SHA for a repository reference.
        
        Args:
            repo: Repository information dictionary
            ref: Reference (branch, tag, commit) to get SHA for (defaults to default branch)
            
        Returns:
            Commit SHA if successful, None otherwise
        """
        specific_ref = ref != ""
        self.log.info(
            f"Getting the commit SHA for {repo['name']}{' at ' + ref if specific_ref else ''}..."
        )
        
        endpoint = f"https://api.github.com/repos/{self.org_name}/{repo['name']}/commits{'/' + ref if specific_ref else ''}"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code != 200:
            self.log.error(
                f"Error getting the commit SHA: status code: {response.status_code}, text: {response.text}"
            )
            return None
        
        response_obj = json.loads(response.text)
        sha = response_obj["sha"] if specific_ref else response_obj[0]["sha"]
        
        self.log.info(
            f"  Commit SHA for {repo['name']} at {'default' if ref == '' else ref} is {sha}"
        )
        return sha
    
    def download_file(self, file_name: str, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Download a file from a URL to a local file.
        
        Args:
            file_name: Local filename to save to
            url: URL to download from
            headers: Optional headers for the request
            
        Returns:
            Filename if successful, None otherwise
        """
        if headers is None:
            headers = {}
        
        self.log.info(f"    Downloading {url} to {file_name}...")
        
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(file_name)
        if dir_path:
            self.ensure_directory_exists(dir_path)
        
        try:
            with requests.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(file_name, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            self.log.error(f"Error downloading {url}: {e}")
            return None
        
        return file_name
    
    def download_export(self, repo_info: Dict[str, Any], file_path: str) -> None:
        """
        Download a migration archive for a repository.
        
        Args:
            repo_info: Repository information dictionary with migration_id
            file_path: Directory path where the export should be saved
        """
        self.log.info(f"Downloading migration archive for {repo_info['name']}...")
        
        if repo_info.get("migration_id") is None:
            self.log.error(f"{repo_info['name']} has no migration ID!")
            return
        
        # Wait for the migration to get ready
        while self.get_migration_status(repo_info["migration_id"]) != "exported":
            time.sleep(1)
        
        # Get the download URL
        endpoint = f"https://api.github.com/orgs/{self.org_name}/migrations/{repo_info['migration_id']}/archive"
        self.log.info(f"Getting migration archive download URL for {repo_info['name']}...")
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code not in [200, 302]:
            self.log.error(
                f"Error downloading migration archive for {repo_info['name']}: status code: {response.status_code}, text: {response.text}"
            )
            return
        
        # Generate standardized filename using base class method
        file_name = self.generate_export_filename(repo_info)
        full_path = os.path.join(file_path, file_name)
        
        self.log.info(f"  Downloading migration archive for {repo_info['name']} to {full_path}...")
        self.download_file(full_path, response.url, headers={})  # Download URL requires empty headers
        self.log.info(f"  Migration archive downloaded for {repo_info['name']}")
    
    def download_repository_archive(self, repo_info: Dict[str, Any], file_path: str, ref: str = "") -> None:
        """
        Download a repository archive for a repository.
        
        Args:
            repo_info: Repository information dictionary with sha
            file_path: Directory path where the archive should be saved
            ref: Reference (branch, tag, commit) to archive
        """
        self.log.info(f"Downloading project archive for {repo_info['name']}...")
        
        if repo_info.get("sha") is None:
            self.log.error(f"{repo_info['name']} has no SHA!")
            return
        
        specific_ref = ref != ""
        url = f"https://api.github.com/repos/{self.org_name}/{repo_info['name']}/tarball/{ref if specific_ref else ''}"
        
        # Generate standardized filename using base class method
        file_name = self.generate_repository_archive_filename(repo_info, repo_info["sha"])
        full_path = os.path.join(file_path, file_name)
        
        self.log.info(f"  Downloading project archive for {repo_info['name']} to {full_path}...")
        self.download_file(full_path, url, headers=self.headers)
        self.log.info(f"  Project archive downloaded for {repo_info['name']}")


def main():
    """Main function to run the GitHub archiver."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="UTC %(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("github_archiver.log"),
            logging.StreamHandler(),
        ],
    )
    logging.Formatter.converter = time.gmtime
    log = logging.getLogger()
    
    # Get configuration from environment
    access_token = os.environ.get("GITHUB_API_TOKEN")
    org_name = os.environ.get("GITHUB_ORG_NAME")
    repositories = os.environ.get("GITHUB_REPOSITORIES")
    
    if not access_token or not org_name:
        log.error("GITHUB_API_TOKEN and GITHUB_ORG_NAME environment variables are required")
        return
    
    # Parse repository filter
    repo_filter = None
    if repositories:
        repositories = repositories.strip().replace(",", " ").replace(";", " ")
        repo_filter = repositories.split()
        log.info(f"Filtering by repositories: {repo_filter}")
    
    # Initialize archiver
    archiver = GitHubArchiver(access_token, org_name)
    export_path = archiver.generate_export_path()
    archiver.ensure_directory_exists(export_path)
    
    # Get repositories
    repos = []
    try:
        repos_raw = archiver.get_repositories()
        for repo in repos_raw:
            # Filter repositories
            if repo_filter:
                repo_in_filter = (str(repo["name"]) in repo_filter) or (str(repo["id"]) in repo_filter)
                if not repo_in_filter:
                    log.info(f"Skipping {repo['name']} - not in filter")
                    continue
            
            r = {"id": repo["id"], "name": repo["name"]}
            repos.append(r)
        
        # Get commit SHAs
        log.info(f"Obtain the commit SHA for {len(repos)} repositories...")
        for r in repos:
            r["sha"] = archiver.get_commit_sha(r)
        
        # Initiate exports
        log.info(f"Initiate export for {len(repos)} repositories...")
        for r in repos:
            r["migration_id"] = archiver.create_migration_export(r)
        
        # Download archives
        log.info(f"Download code and migration archives for {len(repos)} repositories...")
        while repos:
            for i, r in enumerate(repos):
                if r["migration_id"] is None:
                    log.error(f"{r['name']} has no migration ID!")
                    archiver.unlock_repository(r)
                    repos.pop(i)
                    continue
                
                status = archiver.get_migration_status(r["migration_id"])
                if status == "failed":
                    log.error(f"Migration for {r['name']} failed!")
                    archiver.unlock_repository(r)
                    repos.pop(i)
                elif status == "exported":
                    try:
                        archiver.download_repository_archive(r, export_path)
                        archiver.download_export(r, export_path)
                        archiver.unlock_repository(r)
                        repos.pop(i)
                    except Exception as e:
                        log.error(f"Error downloading {r['name']}: {e}")
                        archiver.unlock_repository(r)
                        repos.pop(i)
            time.sleep(1)
    
    finally:
        # Ensure all repositories are unlocked
        for repo in repos:
            archiver.unlock_repository(repo)
    
    log.info("Done!")


if __name__ == "__main__":
    main()
