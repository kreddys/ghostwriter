"""React Agent.

This module defines a custom reasoning and action agent graph.
It invokes tools in a simple loop.
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
logger = logging.getLogger(__name__)

from .graph import create_graph

__version__ = "0.1.0"
__all__ = ["create_graph"]