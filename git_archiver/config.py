import os
import json
import argparse
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path


class ConfigManager:
    """
    Configuration manager that handles settings with priority order:
    1. Default configuration file
    2. Environment variables (override defaults)
    3. Command line arguments (override env vars, with warnings)
    """
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.overrides: Dict[str, str] = {}  # Track what was overridden by CLI
        self.log = logging.getLogger(__name__)
        
        # Load configuration in priority order
        self._load_defaults()
        self._load_environment_overrides()
    
    def _load_defaults(self) -> None:
        """Load default configuration from file."""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                self.log.info(f"Loaded configuration from {config_path}")
            except (json.JSONDecodeError, IOError) as e:
                self.log.warning(f"Failed to load config file {config_path}: {e}")
                self.config = self._get_default_config()
        else:
            self.log.info(f"Config file {config_path} not found, using defaults")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration values."""
        return {
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
                "file_enabled": True,
                "console_enabled": True
            },
            "archive": {
                "base_export_path": "exports",
                "create_directories": True,
                "naming_convention": {
                    "export_format": "export_{name}_{id}_{version}",
                    "repository_format": "repository_archive_{name}_{id}_{sha}",
                    "sanitize_names": True
                }
            },
            "retention": {
                "enable_rotation": True,
                "max_archives_per_repo": 5,
                "max_age_days": 30,
                "min_free_space_gb": 10,
                "cleanup_threshold_gb": 5,
                "cleanup_before_download": True,
                "cleanup_after_download": False
            }
        }
    
    def _load_environment_overrides(self) -> None:
        """Load configuration overrides from environment variables."""
        env_mappings = {
            # GitHub settings
            "GITHUB_API_TOKEN": ("github", "api_token"),
            "GITHUB_ORG_NAME": ("github", "org_name"),
            "GITHUB_REPOSITORIES": ("github", "repositories"),
            "GITHUB_EXPORT_PATH": ("github", "export_path"),
            "GITHUB_PER_PAGE": ("github", "per_page"),
            "GITHUB_RETRY_DELAY": ("github", "retry_delay"),
            
            # GitLab settings
            "GITLAB_API_TOKEN": ("gitlab", "api_token"),
            "GITLAB_URL": ("gitlab", "gitlab_url"),
            "GITLAB_GROUP_ID": ("gitlab", "group_id"),
            "GITLAB_REPOSITORIES": ("gitlab", "repositories"),
            "GITLAB_EXPORT_PATH": ("gitlab", "export_path"),
            "GITLAB_RETRY_DELAY": ("gitlab", "retry_delay"),
            
            # Logging settings
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FORMAT": ("logging", "format"),
            "LOG_FILE_ENABLED": ("logging", "file_enabled"),
            "LOG_CONSOLE_ENABLED": ("logging", "console_enabled"),
            
            # Archive settings
            "ARCHIVE_BASE_PATH": ("archive", "base_export_path"),
            "ARCHIVE_CREATE_DIRS": ("archive", "create_directories"),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                converted_value = self._convert_value(value, section, key)
                self._set_nested_value(self.config, section, key, converted_value)
                self.log.debug(f"Environment override: {env_var} -> {section}.{key} = {converted_value}")
    
    def _convert_value(self, value: str, section: str, key: str) -> Union[str, int, bool]:
        """Convert string values to appropriate types based on context."""
        # Boolean conversions
        if key in ["file_enabled", "console_enabled", "create_directories", "sanitize_names"]:
            return value.lower() in ("true", "1", "yes", "on")
        
        # Integer conversions
        if key in ["per_page", "retry_delay"]:
            try:
                return int(value)
            except ValueError:
                self.log.warning(f"Invalid integer value for {section}.{key}: {value}, using string")
                return value
        
        # Default to string
        return value
    
    def _set_nested_value(self, config: Dict[str, Any], section: str, key: str, value: Any) -> None:
        """Set a nested configuration value."""
        if section not in config:
            config[section] = {}
        config[section][key] = value
    
    def apply_cli_overrides(self, args: argparse.Namespace) -> None:
        """
        Apply command line argument overrides with warnings.
        
        Args:
            args: Parsed command line arguments
        """
        cli_mappings = {
            # GitHub CLI args
            "github_token": ("github", "api_token"),
            "github_org": ("github", "org_name"),
            "github_repos": ("github", "repositories"),
            "github_export_path": ("github", "export_path"),
            
            # GitLab CLI args
            "gitlab_token": ("gitlab", "api_token"),
            "gitlab_url": ("gitlab", "gitlab_url"),
            "gitlab_group": ("gitlab", "group_id"),
            "gitlab_repos": ("gitlab", "repositories"),
            "gitlab_export_path": ("gitlab", "export_path"),
            
            # General CLI args
            "log_level": ("logging", "level"),
            "export_path": ("archive", "base_export_path"),
            
            # Retention CLI args
            "max_archives": ("retention", "max_archives_per_repo"),
            "max_age_days": ("retention", "max_age_days"),
            "min_free_space": ("retention", "min_free_space_gb"),
            "cleanup_threshold": ("retention", "cleanup_threshold_gb"),
        }
        
        for arg_name, (section, key) in cli_mappings.items():
            value = getattr(args, arg_name, None)
            if value is not None:
                old_value = self.get(f"{section}.{key}")
                self._set_nested_value(self.config, section, key, value)
                self.overrides[f"{section}.{key}"] = f"CLI argument --{arg_name.replace('_', '-')}"
                
                # Warn about override
                self.log.warning(
                    f"Configuration override: {section}.{key} changed from '{old_value}' to '{value}' "
                    f"by command line argument --{arg_name.replace('_', '-')}"
                )
        
        # Handle special retention flags
        if hasattr(args, 'force_cleanup') and args.force_cleanup:
            self._set_nested_value(self.config, "retention", "cleanup_threshold_gb", 999999)  # Force cleanup
            self.overrides["retention.cleanup_threshold_gb"] = "CLI argument --force-cleanup"
            self.log.warning("Forced cleanup enabled - will clean up regardless of disk space")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'github.api_token')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Dictionary containing the section configuration
        """
        return self.config.get(section, {})
    
    def validate_required_settings(self, platform: str) -> bool:
        """
        Validate that required settings are present for a platform.
        
        Args:
            platform: Platform name ('github' or 'gitlab')
            
        Returns:
            True if all required settings are present, False otherwise
        """
        required_settings = {
            "github": ["api_token", "org_name"],
            "gitlab": ["api_token", "group_id"]
        }
        
        if platform not in required_settings:
            self.log.error(f"Unknown platform: {platform}")
            return False
        
        missing_settings = []
        for setting in required_settings[platform]:
            value = self.get(f"{platform}.{setting}")
            if not value:
                missing_settings.append(f"{platform}.{setting}")
        
        if missing_settings:
            self.log.error(f"Missing required settings for {platform}: {', '.join(missing_settings)}")
            return False
        
        return True
    
    def save_config(self, file_path: Optional[str] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            file_path: Optional path to save to (defaults to original config file)
        """
        save_path = file_path or self.config_file
        
        try:
            with open(save_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.log.info(f"Configuration saved to {save_path}")
        except IOError as e:
            self.log.error(f"Failed to save configuration to {save_path}: {e}")
    
    def print_overrides(self) -> None:
        """Print information about configuration overrides."""
        if self.overrides:
            self.log.info("Configuration overrides applied:")
            for key, source in self.overrides.items():
                value = self.get(key)
                self.log.info(f"  {key} = '{value}' (from {source})")
        else:
            self.log.info("No configuration overrides applied")


def create_default_config_file(file_path: str = "config.json") -> None:
    """
    Create a default configuration file.
    
    Args:
        file_path: Path where to create the config file
    """
    config_manager = ConfigManager()
    default_config = config_manager._get_default_config()
    
    try:
        with open(file_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Default configuration file created at {file_path}")
    except IOError as e:
        print(f"Failed to create config file {file_path}: {e}")


if __name__ == "__main__":
    # Create default config file if run directly
    create_default_config_file()