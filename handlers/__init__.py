# handlers/__init__.py
from . import registration
from . import service_choice
from . import create_task
from . import debug
from . import archive
from . import stats
from . import graph

__all__ = [
    "registration",
    "service_choice",
    "create_task",
    "debug",
    "archive",
    "stats",
    "graph",
]
