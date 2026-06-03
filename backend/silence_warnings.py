"""
backend/silence_warnings.py
─────────────────────────────
Suppress known benign warnings at the process level.
Import this module at the top of any entry point (main.py, reset_and_run.py, etc.)
BEFORE any other imports to prevent FutureWarnings from being printed to stderr.
"""

import warnings

# google.generativeai is deprecated but still functional; suppress FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
warnings.filterwarnings("ignore", message=".*google.generativeai.*", category=FutureWarning)
