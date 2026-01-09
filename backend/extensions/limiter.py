from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Shared rate limiter instance for use across modules
# Default limits: 200/day and 50/hour (sensible app-wide defaults)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    enabled=True,
)
