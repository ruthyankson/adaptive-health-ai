"""
Constants and configuration values for the application.

This module defines all static constants, configuration parameters, and
enumerated values used throughout the application. Organizing constants
in a centralized location improves maintainability and makes it easier
to update values across the codebase.

Sections:
    - API Configuration: API endpoints, timeouts, and authentication settings
    - Database Configuration: Database connection parameters and settings
    - Application Settings: General application configuration and behavior
    - Error Messages: Standard error message templates
    - Status Codes: Application-specific status and return codes
    - Limits: Boundaries, thresholds, and quotas
    - Paths: File system and resource paths
"""

from __future__ import annotations

from pathlib import Path

# Paths

# Project root = folder containing this file's grandparent (src/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
META_DATA_DIR = DATA_DIR / "metadata"

DATA_PATH = RAW_DATA_DIR / "LLCP2024.XPT"
COLUMNS_OUT_PATH = META_DATA_DIR / "columns.csv"
