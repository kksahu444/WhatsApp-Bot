"""
Database Migration Script
Handles database schema migrations using Alembic
"""

import logging
import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_alembic_command(command: list, cwd: Path = None):
    """Run an Alembic command."""
    if cwd is None:
        cwd = Path(__file__).parent.parent
    
    full_command = ["alembic"] + command
    
    logger.info(f"Running: {' '.join(full_command)}")
    
    try:
        result = subprocess.run(
            full_command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout:
            print(result.stdout)
        
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Alembic command failed: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False


def upgrade(revision: str = "head"):
    """Upgrade database to a specific revision."""
    logger.info(f"Upgrading database to: {revision}")
    return run_alembic_command(["upgrade", revision])


def downgrade(revision: str = "-1"):
    """Downgrade database by a specific number of revisions."""
    logger.info(f"Downgrading database: {revision}")
    return run_alembic_command(["downgrade", revision])


def current():
    """Show current revision."""
    logger.info("Checking current revision...")
    return run_alembic_command(["current"])


def history():
    """Show migration history."""
    logger.info("Migration history:")
    return run_alembic_command(["history", "--verbose"])


def create_migration(message: str):
    """Create a new migration."""
    logger.info(f"Creating migration: {message}")
    return run_alembic_command(["revision", "--autogenerate", "-m", message])


def stamp(revision: str = "head"):
    """Stamp the database with a specific revision without running migrations."""
    logger.info(f"Stamping database: {revision}")
    return run_alembic_command(["stamp", revision])


def heads():
    """Show current heads."""
    return run_alembic_command(["heads"])


def branches():
    """Show current branches."""
    return run_alembic_command(["branches"])


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration tool")
    subparsers = parser.add_subparsers(dest="command", help="Migration commands")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade to a revision")
    upgrade_parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Target revision (default: head)"
    )
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade revisions")
    downgrade_parser.add_argument(
        "revision",
        nargs="?",
        default="-1",
        help="Target revision or -N for N steps back (default: -1)"
    )
    
    # Current command
    subparsers.add_parser("current", help="Show current revision")
    
    # History command
    subparsers.add_parser("history", help="Show migration history")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument(
        "message",
        help="Migration message"
    )
    
    # Stamp command
    stamp_parser = subparsers.add_parser("stamp", help="Stamp database revision")
    stamp_parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Revision to stamp (default: head)"
    )
    
    # Heads command
    subparsers.add_parser("heads", help="Show current heads")
    
    # Branches command
    subparsers.add_parser("branches", help="Show current branches")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Check Alembic is installed
    try:
        subprocess.run(
            ["alembic", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Alembic is not installed. Run: pip install alembic")
        sys.exit(1)
    
    # Run the command
    success = False
    
    if args.command == "upgrade":
        success = upgrade(args.revision)
    elif args.command == "downgrade":
        success = downgrade(args.revision)
    elif args.command == "current":
        success = current()
    elif args.command == "history":
        success = history()
    elif args.command == "create":
        success = create_migration(args.message)
    elif args.command == "stamp":
        success = stamp(args.revision)
    elif args.command == "heads":
        success = heads()
    elif args.command == "branches":
        success = branches()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
