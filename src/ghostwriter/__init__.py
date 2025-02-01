"""GhostWriter.

This module defines an AI-powered news article generation and publishing system.
It manages workflows for content creation and CMS integration.
"""

import logging
import logging.config

# Use logging.conf instead of basicConfig
logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

# Create logger for this package
logger = logging.getLogger('ghostwriter')

from .graph import create_graph

__version__ = "0.1.0"
__all__ = ["create_graph"]