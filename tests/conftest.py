"""Pytest configuration for office2pdf tests."""

from dotenv import load_dotenv

# Load .env file if it exists
# python-dotenv automatically searches up the directory tree
# This allows integration tests to use credentials from .env
load_dotenv()
