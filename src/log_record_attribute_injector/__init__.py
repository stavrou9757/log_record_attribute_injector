"""Log Record Attribute Injector.

A logging.Filter subclass that adds predefined attributes to every
LogRecord before it reaches formatters.
"""

from .core import AttributeInjector

__all__ = ["AttributeInjector"]
