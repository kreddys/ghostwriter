"""React Agent.

This module defines a custom reasoning and action agent graph.
It invokes tools in a simple loop.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Generate timestamp for the log file
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(LOG_DIR, f'react_agent_{timestamp}.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Console handler
        logging.StreamHandler(),
        # File handler with timestamp in filename
        logging.FileHandler(log_file)
    ]
)

# Create logger for this package
logger = logging.getLogger(__name__)

from .graph import create_graph

__version__ = "0.1.0"
__all__ = ["create_graph"]