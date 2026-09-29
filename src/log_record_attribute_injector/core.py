"""Core implementation of the AttributeInjector logging filter."""

import logging
import socket


class AttributeInjector(logging.Filter):
    """A logging.Filter that injects fixed attributes onto each LogRecord.

    Standard logging formatters can reference any attribute present on a
    LogRecord via %(name)s. This filter populates a configurable set of
    attributes once, at filter time, so that every record downstream sees
    them without callers having to thread context manually.

    Design decisions:

    * Values are computed once in __init__ and reused. This keeps filter()
      cheap (a loop of setattr calls) and, more importantly, makes the
      injected values deterministic for a given filter instance. The
    * hostname is resolved via socket.gethostname() at construction time.
      Resolving per-record would be wasteful and would make records
      non-deterministic if the hostname changed under a long-running
      process. If resolution fails we fall back to a stable sentinel
      string rather than propagating the exception, because a logging
      filter that raises will break the handler that uses it.
    * If a caller passes an attribute whose name collides with a reserved
      LogRecord field (e.g. "msg", "levelno", "created"), we raise
      ValueError at construction. Overwriting those silently would produce
      subtly broken records that are extremely hard to debug.
    * If a LogRecord already carries one of the requested attributes (set
      by logging.LoggerAdapter or by an earlier filter), we overwrite it.
      The point of this filter is to guarantee the attribute is present
      with a known value; honouring a pre-existing value would make that
      guarantee conditional and surprising.
    """

    # Attributes defined by logging.LogRecord.__init__ that we must never
    # overwrite, because formatters and handlers depend on their semantics.
    _RESERVED = frozenset(
        {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "taskName",
        }
    )

    def __init__(self, attributes):
        """Initialise the filter.

        Args:
            attributes: A mapping of attribute name -> value to inject onto
                each LogRecord. Names must be valid Python identifiers and
                must not collide with reserved LogRecord fields.

        Raises:
            ValueError: If a name is reserved or not a valid identifier.
        """
        super().__init__()

        if not isinstance(attributes, dict):
            raise TypeError(
                "attributes must be a dict, got %r" % type(attributes).__name__
            )

        normalised = {}
        for name, value in attributes.items():
            if not isinstance(name, str):
                raise TypeError(
                    "attribute name must be str, got %r" % type(name).__name__
                )
            if not name.isidentifier():
                raise ValueError(
                    "attribute name %r is not a valid identifier" % name
                )
            if name in self._RESERVED:
                raise ValueError(
                    "attribute name %r collides with a reserved "
                    "LogRecord field" % name
                )
            normalised[name] = value

        # Store as a list of pairs so filter() iterates without allocating.
        self._attributes = list(normalised.items())
        self._attribute_names = sorted(normalised.keys())

    @classmethod
    def with_hostname(cls, hostname=None, **extra):
        """Build an injector that includes a ``hostname`` attribute.

        Args:
            hostname: Explicit hostname. If None, socket.gethostname() is
                called once; on failure the sentinel "<unknown>" is used.
            **extra: Additional attributes to inject alongside hostname.

        Returns:
            AttributeInjector instance.
        """
        if hostname is None:
            try:
                hostname = socket.gethostname()
            except OSError:
                hostname = "<unknown>"
        attrs = {"hostname": hostname}
        attrs.update(extra)
        return cls(attrs)

    @property
    def attribute_names(self):
        """Sorted tuple of attribute names this filter injects."""
        return tuple(self._attribute_names)

    def filter(self, record):
        """Inject attributes onto *record*.

        Always returns True so the record continues through the pipeline.
        Existing values of the injected attributes are overwritten by design
        (see class docstring).
        """
        for name, value in self._attributes:
            setattr(record, name, value)
        return True
