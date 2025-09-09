# Git Archiver

A comprehensive tool for archiving repositories from GitHub and GitLab with standardized naming conventions, flexible configuration management, and common functionality.

## Features

- **Multi-Platform Support**: Archive repositories from GitHub and GitLab
- **Standardized Archive Naming**: Consistent naming patterns across platforms
- **Flexible Configuration**: Configuration file, environment variables, and command-line arguments
- **Priority-Based Settings**: Clear override hierarchy with warnings
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

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
