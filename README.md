# Log Record Attribute Injector

`AttributeInjector` is a `logging.Filter` subclass that stamps a fixed set of
attributes onto every `LogRecord` before it reaches formatters, so you can
reference things like `%(request_id)s` and `%(hostname)s` in a format string
without callers having to pass them in.

## Usage

```python
import logging
from log_record_attribute_injector import AttributeInjector

logger = logging.getLogger("app")
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s %(hostname)s %(request_id)s %(message)s")
)
handler.addFilter(
    AttributeInjector.with_hostname(request_id="req-0001")
)
logger.addHandler(handler)

logger.info("starting up")
# 2025-01-01 12:00:00,000 web-01 req-0001 starting up
```

Exported names:

- `AttributeInjector(attributes: dict)` — constructor.
- `AttributeInjector.with_hostname(hostname=None, **extra)` — convenience
  builder that adds a `hostname` attribute.
- `AttributeInjector.filter(record)` — injects attributes, always returns
  `True`.
- `AttributeInjector.attribute_names` — sorted tuple of injected names.

## Why this exists

When every log line needs a `request_id` or `hostname`, threading those values
through every call site is noisy and easy to forget. A filter is the cheapest
place to guarantee an attribute exists on every record that flows through a
handler.

The trade-off: the values are fixed for the lifetime of the filter. This is
deliberate. If you need per-request `request_id`, use a `LoggerAdapter` or
`logging.setLogRecordFactory` instead — this library is for attributes that are
stable per handler, like `hostname` or a deployment `env` tag.

## Edge cases

- If an attribute name collides with a reserved `LogRecord` field (`msg`,
  `levelno`, `created`, etc.), the constructor raises `ValueError`. Overwriting
  those silently produces records that break in ways that are very hard to
  trace.
- If a record already carries one of the injected attributes (set by an earlier
  filter or adapter), this filter **overwrites** it. The guarantee is that the
  attribute is present with the configured value, not that it is preserved.
- `with_hostname()` resolves the hostname once at construction via
  `socket.gethostname()`. If that call fails it falls back to the sentinel
  string `<unknown>` rather than raising, because a filter that raises will
  disable its handler.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
