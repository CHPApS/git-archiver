import argparse
import logging
import sys
from typing import Optional
from .config import ConfigManager


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Git Archiver - Archive repositories from GitHub and GitLab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration Priority (highest to lowest):
  1. Command line arguments (with warnings)
  2. Environment variables
  3. Configuration file (config.json)
  4. Built-in defaults

Examples:
  # Archive GitHub repositories
  python -m git_archiver github --github-token TOKEN --github-org myorg
  
  # Archive GitLab repositories
  python -m git_archiver gitlab --gitlab-token TOKEN --gitlab-group 12345
  
  # Use configuration file with environment overrides
  export GITHUB_API_TOKEN=your_token
  python -m git_archiver github
  
  # Override specific settings with CLI args (will show warnings)
  python -m git_archiver github --export-path /custom/path
        """
    )
    
    # Platform selection
    subparsers = parser.add_subparsers(dest='platform', help='Platform to archive from')
    
    # GitHub subcommand
    github_parser = subparsers.add_parser('github', help='Archive from GitHub')
    _add_github_arguments(github_parser)
    
    # GitLab subcommand
    gitlab_parser = subparsers.add_parser('gitlab', help='Archive from GitLab')
    _add_gitlab_arguments(gitlab_parser)
    
    # Config subcommand
    config_parser = subparsers.add_parser('config', help='Configuration management')
    _add_config_arguments(config_parser)
    
    # Global arguments
    _add_global_arguments(parser)
    
    return parser


def _add_github_arguments(parser: argparse.ArgumentParser) -> None:
    """Add GitHub-specific arguments."""
    github_group = parser.add_argument_group('GitHub Settings')
    
    github_group.add_argument(
        '--github-token',
        help='GitHub API token (overrides GITHUB_API_TOKEN env var and config file)'
    )
    
    github_group.add_argument(
        '--github-org',
        help='GitHub organization name (overrides GITHUB_ORG_NAME env var and config file)'
    )
    
    github_group.add_argument(
        '--github-repos',
        help='Comma-separated list of repository names or IDs to filter (overrides GITHUB_REPOSITORIES env var and config file)'
    )
    
    github_group.add_argument(
        '--github-export-path',
        help='Custom export path for GitHub archives (overrides config file)'
    )
    
    # Add common arguments to GitHub parser
    _add_common_arguments(parser)


def _add_gitlab_arguments(parser: argparse.ArgumentParser) -> None:
    """Add GitLab-specific arguments."""
    gitlab_group = parser.add_argument_group('GitLab Settings')
    
    gitlab_group.add_argument(
        '--gitlab-token',
        help='GitLab API token (overrides GITLAB_API_TOKEN env var and config file)'
    )
    
    gitlab_group.add_argument(
        '--gitlab-url',
        help='GitLab instance URL (overrides GITLAB_URL env var and config file)'
    )
    
    gitlab_group.add_argument(
        '--gitlab-group',
        help='GitLab group ID or name (overrides GITLAB_GROUP_ID env var and config file)'
    )
    
    gitlab_group.add_argument(
        '--gitlab-repos',
        help='Comma-separated list of repository names or IDs to filter (overrides GITLAB_REPOSITORIES env var and config file)'
    )
    
    gitlab_group.add_argument(
        '--gitlab-export-path',
        help='Custom export path for GitLab archives (overrides config file)'
    )
    
    # Add common arguments to GitLab parser
    _add_common_arguments(parser)


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    """Add configuration management arguments."""
    config_group = parser.add_argument_group('Configuration Actions')
    
    config_group.add_argument(
        '--create-default',
        action='store_true',
        help='Create a default configuration file'
    )
    
    config_group.add_argument(
        '--show-config',
        action='store_true',
        help='Show current configuration (after applying env vars)'
    )
    
    config_group.add_argument(
        '--validate',
        choices=['github', 'gitlab'],
        help='Validate configuration for specified platform'
    )


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to subparsers."""
    common_group = parser.add_argument_group('Common Options')
    
    common_group.add_argument(
        '--export-path',
        help='Base export path (overrides config file)'
    )
    
    common_group.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (overrides config file)'
    )
    
    common_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )
    
    common_group.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )


def _add_global_arguments(parser: argparse.ArgumentParser) -> None:
    """Add global arguments."""
    global_group = parser.add_argument_group('Global Settings')
    
    global_group.add_argument(
        '--config-file',
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )


def setup_logging(config: ConfigManager, verbose: bool = False, platform: str = 'git_archiver') -> None:
    """
    Setup logging based on configuration.
    
    Args:
        config: Configuration manager instance
        verbose: Enable verbose logging
        platform: Platform name for log file naming
    """
    log_config = config.get_section('logging')
    
    # Determine log level
    level = log_config.get('level', 'INFO')
    if verbose:
        level = 'DEBUG'
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Setup handlers
    handlers = []
    
    if log_config.get('console_enabled', True):
        handlers.append(logging.StreamHandler())
    
    if log_config.get('file_enabled', True):
        # Create platform-specific log file
        log_file = f"{platform}_archiver.log"
        handlers.append(logging.FileHandler(log_file))
    
    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format=log_config.get('format', '%(asctime)s [%(levelname)s] %(message)s'),
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Use UTC time
    import time
    logging.Formatter.converter = time.gmtime


def handle_config_commands(args: argparse.Namespace, config: ConfigManager) -> bool:
    """
    Handle configuration-related commands.
    
    Args:
        args: Parsed command line arguments
        config: Configuration manager instance
        
    Returns:
        True if a config command was handled (should exit), False otherwise
    """
    if args.platform != 'config':
        return False
    
    if args.create_default:
        from .config import create_default_config_file
        create_default_config_file(args.config_file)
        return True
    
    if args.show_config:
        import json
        print("Current configuration:")
        print(json.dumps(config.config, indent=2))
        config.print_overrides()
        return True
    
    if args.validate:
        platform = args.validate
        if config.validate_required_settings(platform):
            print(f"✓ Configuration for {platform} is valid")
        else:
            print(f"✗ Configuration for {platform} is invalid")
            sys.exit(1)
        return True
    
    # If no specific config command, show help
    print("No configuration command specified. Use --help for available options.")
    return True


def parse_arguments(argv: Optional[list] = None) -> tuple[argparse.Namespace, ConfigManager]:
    """
    Parse command line arguments and setup configuration.
    
    Args:
        argv: Optional argument list (for testing)
        
    Returns:
        Tuple of (parsed arguments, configuration manager)
    """
    parser = create_argument_parser()
    args = parser.parse_args(argv)
    
    # Initialize configuration manager
    config = ConfigManager(args.config_file)
    
    # Apply CLI overrides
    config.apply_cli_overrides(args)
    
    # Setup logging
    platform = args.platform if hasattr(args, 'platform') and args.platform else 'git_archiver'
    setup_logging(config, args.verbose if hasattr(args, 'verbose') else False, platform)
    
    return args, config


def main() -> None:
    """Main CLI entry point."""
    try:
        args, config = parse_arguments()
        
        # Handle configuration commands
        if handle_config_commands(args, config):
            return
        
        # Validate platform selection
        if not args.platform:
            print("Error: No platform specified. Use 'github', 'gitlab', or 'config'.")
            sys.exit(1)
        
        if args.platform not in ['github', 'gitlab']:
            print(f"Error: Unknown platform '{args.platform}'. Use 'github' or 'gitlab'.")
            sys.exit(1)
        
        # Validate required configuration
        if not config.validate_required_settings(args.platform):
            print(f"Error: Missing required configuration for {args.platform}")
            sys.exit(1)
        
        # Show configuration overrides
        config.print_overrides()
        
        # Import and run the appropriate archiver
        if args.platform == 'github':
            from .github_archiver import main as github_main
            github_main(config, args)
        elif args.platform == 'gitlab':
            from .gitlab_archiver import main as gitlab_main
            gitlab_main(config, args)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()