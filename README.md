# Git Archiver

A comprehensive tool for archiving repositories from GitHub and GitLab with standardized naming conventions, flexible configuration management, and common functionality.

## Features

- **Multi-Platform Support**: Archive repositories from GitHub and GitLab
- **Standardized Archive Naming**: Consistent naming patterns across platforms
- **Flexible Configuration**: Configuration file, environment variables, and command-line arguments
- **Priority-Based Settings**: Clear override hierarchy with warnings
- **Archive Rotation**: Intelligent backup rotation with configurable retention policies
- **Disk Space Monitoring**: Automatic cleanup when running low on storage
- **Dry Run Mode**: Test operations without making actual changes
- **Comprehensive Logging**: Structured logging with UTC timestamps

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd git-archiver

# Install dependencies using Poetry
poetry install

# Activate the virtual environment
poetry shell
```

## Quick Start

### 1. Create Configuration File

```bash
poetry run python -m git_archiver config --create-default
```

This creates a `config.json` file with default settings.

### 2. Configure Your Settings

Edit `config.json` or use environment variables:

```bash
# GitHub
export GITHUB_API_TOKEN="your_github_token"
export GITHUB_ORG_NAME="your_organization"

# GitLab
export GITLAB_API_TOKEN="your_gitlab_token"
export GITLAB_GROUP_ID="your_group_id"
```

### 3. Archive Repositories

```bash
# Archive GitHub repositories
poetry run python -m git_archiver github

# Archive GitLab repositories
poetry run python -m git_archiver gitlab

# Dry run to see what would happen
poetry run python -m git_archiver github --dry-run
```

## Configuration

### Configuration Priority (Highest to Lowest)

1. **Command Line Arguments** (with warnings when overriding)
2. **Environment Variables**
3. **Configuration File** (`config.json`)
4. **Built-in Defaults**

### Configuration File Structure

```json
{
  "github": {
    "api_token": "",
    "org_name": "",
    "repositories": "",
    "export_path": "exports/github",
    "per_page": 100,
    "retry_delay": 1
  },
  "gitlab": {
    "api_token": "",
    "gitlab_url": "https://gitlab.com",
    "group_id": "",
    "repositories": "",
    "export_path": "exports/gitlab",
    "retry_delay": 1
  },
  "logging": {
    "level": "INFO",
    "format": "UTC %(asctime)s [%(levelname)s] %(message)s",
    "file_enabled": true,
    "console_enabled": true
  },
  "archive": {
    "base_export_path": "exports",
    "create_directories": true,
    "naming_convention": {
      "export_format": "export_{name}_{id}_{version}",
      "repository_format": "repository_archive_{name}_{id}_{sha}",
      "sanitize_names": true
    }
  },
  "retention": {
    "enable_rotation": true,
    "max_archives_per_repo": 5,
    "max_age_days": 30,
    "min_free_space_gb": 10,
    "cleanup_threshold_gb": 5,
    "cleanup_before_download": true,
    "cleanup_after_download": false
  }
}
```

### Environment Variables

| Variable | Description | Platform |
|----------|-------------|----------|
| `GITHUB_API_TOKEN` | GitHub API token | GitHub |
| `GITHUB_ORG_NAME` | GitHub organization name | GitHub |
| `GITHUB_REPOSITORIES` | Comma-separated repository filter | GitHub |
| `GITLAB_API_TOKEN` | GitLab API token | GitLab |
| `GITLAB_GROUP_ID` | GitLab group ID or name | GitLab |
| `GITLAB_URL` | GitLab instance URL | GitLab |
| `GITLAB_REPOSITORIES` | Comma-separated repository filter | GitLab |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | Global |
| `GIT_ARCHIVER_CONFIG` | Path to configuration file | Global |

## Usage Examples

### Basic Usage

```bash
# Archive all repositories from GitHub organization
poetry run python -m git_archiver github --github-token TOKEN --github-org myorg

# Archive specific repositories
poetry run python -m git_archiver github --github-repos "repo1,repo2,repo3"

# Archive from GitLab group
poetry run python -m git_archiver gitlab --gitlab-token TOKEN --gitlab-group 12345

# Use custom export path
poetry run python -m git_archiver github --export-path /custom/path
```

### Configuration Management

```bash
# Show current configuration
poetry run python -m git_archiver config --show-config

# Validate configuration for a platform
poetry run python -m git_archiver config --validate github
poetry run python -m git_archiver config --validate gitlab

# Create new default configuration
poetry run python -m git_archiver config --create-default
```

### Advanced Usage

```bash
# Dry run with verbose output
poetry run python -m git_archiver github --dry-run --verbose

# Override log level
poetry run python -m git_archiver github --log-level DEBUG

# Use custom configuration file
poetry run python -m git_archiver --config-file custom-config.json github

# Archive rotation and retention
poetry run python -m git_archiver github --max-archives 3 --max-age-days 14
poetry run python -m git_archiver github --force-cleanup
poetry run python -m git_archiver github --no-rotation
```

## Archive Rotation & Retention

The tool includes intelligent archive rotation to manage disk space and maintain a clean archive history.

### Retention Policies

- **Archive Count Limit**: Maximum number of archives per repository
- **Age-Based Cleanup**: Remove archives older than specified days
- **Disk Space Monitoring**: Automatic cleanup when free space is low
- **Aggressive Cleanup**: More aggressive removal when critically low on space

### Retention Configuration

```json
{
  "retention": {
    "enable_rotation": true,
    "max_archives_per_repo": 5,
    "max_age_days": 30,
    "min_free_space_gb": 10,
    "cleanup_threshold_gb": 5,
    "cleanup_before_download": true,
    "cleanup_after_download": false
  }
}
```

### Retention Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `enable_rotation` | Enable/disable archive rotation | `true` |
| `max_archives_per_repo` | Maximum archives to keep per repository | `5` |
| `max_age_days` | Maximum age of archives in days | `30` |
| `min_free_space_gb` | Minimum free space before cleanup (GB) | `10` |
| `cleanup_threshold_gb` | Aggressive cleanup threshold (GB) | `5` |
| `cleanup_before_download` | Clean up before downloading new archives | `true` |
| `cleanup_after_download` | Clean up after downloading new archives | `false` |

### Retention CLI Arguments

```bash
# Override retention settings
poetry run python -m git_archiver github --max-archives 3
poetry run python -m git_archiver github --max-age-days 14
poetry run python -m git_archiver github --min-free-space 5.0
poetry run python -m git_archiver github --cleanup-threshold 2.0

# Force cleanup regardless of disk space
poetry run python -m git_archiver github --force-cleanup

# Disable rotation for this run
poetry run python -m git_archiver github --no-rotation
```

### Archive Management Commands

```bash
# Manual cleanup of archives
poetry run python -m git_archiver config --cleanup exports/github

# Show retention summary
poetry run python -m git_archiver config --retention-summary exports/github

# Example output:
# Retention Summary for: exports/github
#   Total Archives: 15
#   Total Repositories: 3
#   Total Size: 245.7MB
#   Oldest Archive: 25.3 days
#   Newest Archive: 0.1 days
#   Disk Usage: 125.4GB used, 89.2GB free
#   Low Space Warning: No
```

## Archive Naming Convention

The tool uses standardized naming patterns for consistency:

### Export Archives
- **Format**: `export_{name}_{id}[_{version}].{extension}`
- **GitHub Example**: `export_my-repo_12345.tar.gz`
- **GitLab Example**: `export_my-project_67890_15.0.tgz`

### Repository Archives
- **Format**: `repository_archive_{name}_{id}_{sha}.{extension}`
- **GitHub Example**: `repository_archive_my-repo_12345_abc123def.tar.gz`
- **GitLab Example**: `repository_archive_my-project_67890_xyz789abc.tgz`

## API Requirements

### GitHub
- **Token Scopes**: `repo`, `admin:org`
- **Permissions**: Read access to organization repositories

### GitLab
- **Token Scopes**: `api`
- **Permissions**: Read access to group projects

## Architecture

### Base Classes
- **`BaseArchiver`**: Common functionality and naming conventions
- **`ConfigManager`**: Configuration management with priority handling

### Platform-Specific Classes
- **`GitHubArchiver`**: GitHub API integration
- **`GitLabArchiver`**: GitLab API integration

### CLI Interface
- **`cli.py`**: Command-line interface with argument parsing
- **`__main__.py`**: Package entry point

## Development

### Project Structure
```
git_archiver/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── base_archiver.py     # Base archiver class
├── config.py            # Configuration management
├── cli.py               # Command-line interface
├── github_archiver.py   # GitHub implementation
└── gitlab_archiver.py   # GitLab implementation
```

### Adding New Platforms

1. Create a new archiver class inheriting from `BaseArchiver`
2. Implement required abstract methods
3. Add platform-specific CLI arguments
4. Update configuration schema

## Troubleshooting

### Common Issues

1. **Missing API Token**: Ensure tokens are set in config, environment, or CLI
2. **Permission Errors**: Verify token has required scopes
3. **Network Issues**: Check connectivity to GitHub/GitLab APIs
4. **Path Issues**: Ensure export directories are writable

### Debug Mode

```bash
# Enable debug logging
poetry run python -m git_archiver github --log-level DEBUG --verbose
```

### Configuration Validation

```bash
# Check if configuration is valid
poetry run python -m git_archiver config --validate github
poetry run python -m git_archiver config --show-config
```

### Archive Management

```bash
# Check current archive status
poetry run python -m git_archiver config --retention-summary exports/github

# Clean up old archives manually
poetry run python -m git_archiver config --cleanup exports/github

# Archive with custom retention
poetry run python -m git_archiver github --max-archives 2 --max-age-days 7
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
