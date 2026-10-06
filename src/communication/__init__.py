"""Communication primitives shared by coordinator and workers."""

from .message_queue import MessageQueue

__all__ = ["MessageQueue"]
