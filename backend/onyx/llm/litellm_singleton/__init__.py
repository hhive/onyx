"""
Singleton module for litellm configuration.
This ensures litellm is configured exactly once when first imported.
All other modules should import litellm from here instead of directly.
"""

import os

import litellm

from .config import initialize_litellm
from .monkey_patches import apply_monkey_patches

if os.environ.get("ONYX_SKIP_LITELLM_INIT", "").lower() != "true":
    initialize_litellm()
    apply_monkey_patches()

# Export the configured litellm module and model
__all__ = ["litellm"]
