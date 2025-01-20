"""GhostWriter.

This module defines an AI-powered news article generation and publishing system.
It manages workflows for content creation and CMS integration.
"""

import logging

# Configure logging for detailed console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create logger for this package
logger = logging.getLogger('ghostwriter')

from .graph import create_graph

__version__ = "0.1.0"
__all__ = ["create_graph"]
