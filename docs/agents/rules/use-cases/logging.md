# Use case logging

Read when writing or reviewing a use case.

- Always add logging to use cases. It is the main record of what they did.
- Log business events at `info`, such as what was created or that a title had no match.
- Log accepted problems at `warning`, such as a skipped movie.
- Log lower-level details at `debug`.
- Never log an error you are raising. Whoever catches it decides, so it isn't logged twice.
- Never log personal data.

```python
logger = logging.getLogger(__name__)

# Business event: info.
logger.info("Added %d movies for cinema %s", len(movies), cinema_id)

# Lower-level detail: debug.
logger.debug("Matching title %s", title)

# Accepted problem: warning.
logger.warning("Skipped enrichment for movie %s: %s", movie_id, reason)

# Prohibited: logging an error you raise. The caller decides how to log it.
logger.error("Cinema %s not found", cinema_id)
raise CinemaNotFoundError(f"Cinema '{cinema_id}' not found")
```
