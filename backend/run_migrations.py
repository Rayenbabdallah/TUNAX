"""Apply Alembic migrations"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

os.chdir(backend_dir)

from alembic.config import Config
from alembic import command

# Set up config
alembic_cfg = Config('migrations/alembic.ini')
alembic_cfg.set_main_option('script_location', 'migrations')
alembic_cfg.set_main_option('sqlalchemy.url', f'sqlite:///{backend_dir}/tunax.db')

# Run upgrade
print("Running migrations...")
command.upgrade(alembic_cfg, 'head')
print("✓ Migrations complete!")
