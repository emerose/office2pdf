"""Pytest configuration for office2pdf tests."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root if it exists
# This allows integration tests to use credentials from .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
