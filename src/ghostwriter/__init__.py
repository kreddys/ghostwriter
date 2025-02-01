import os
import logging
import logging.config

# Get the directory containing logging.conf
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logging.conf')

# Use logging.conf instead of basicConfig
logging.config.fileConfig(config_path, disable_existing_loggers=False)

# Create logger for this package
logger = logging.getLogger('ghostwriter')

from .graph import create_graph

__version__ = "0.1.0"
__all__ = ["create_graph"]