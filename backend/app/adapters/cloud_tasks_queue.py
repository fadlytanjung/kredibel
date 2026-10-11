"""Cloud Tasks queue adapter (spec 004 plan).

Re-exports CloudTasksQueue and InlineTaskQueue from app.adapters.cloud_tasks.
"""

from app.adapters.cloud_tasks import CloudTasksQueue, InlineTaskQueue

__all__ = ["CloudTasksQueue", "InlineTaskQueue"]
