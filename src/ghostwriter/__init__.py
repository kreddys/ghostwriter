import os
import logging
import logging.config
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Get the directory containing logging.conf
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logging.conf')

# Use logging.conf instead of basicConfig
logging.config.fileConfig(config_path, disable_existing_loggers=False)

# Create logger for this package
logger = logging.getLogger('ghostwriter')

# Initialize Sentry
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[LoggingIntegration()],
    traces_sample_rate=0.0,  # Disable tracing
    send_default_pii=True,
    auto_session_tracking=True,
    max_breadcrumbs=0,  # Disable breadcrumbs
)

from .graph import create_graph

__version__ = "0.1.0"
__all__ = ["create_graph"]
