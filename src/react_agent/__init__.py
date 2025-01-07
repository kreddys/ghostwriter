"""React Agent.

This module defines a custom reasoning and action agent graph.
It invokes tools in a simple loop.
"""

import os
import logging
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Console handler
        logging.StreamHandler(),
        # File handler with path suitable for Docker
        logging.FileHandler(os.path.join(LOG_DIR, 'react_agent.log'))
    ]
)

# Create logger for this package
logger = logging.getLogger(__name__)

from .graph import create_graph

__version__ = "0.1.0"
__all__ = ["create_graph"]