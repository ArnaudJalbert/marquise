# Use case failure

Read when deciding what happens if something goes wrong in a use case.

- A use case never falls back. Its job is to execute business logic on the input it receives, so it doesn't guess at missing input or substitute for it.
- Missing or invalid mandatory input fails as early as possible, before any work is done.
- A use case reports failure by raising an exception. It returns output only when it executed correctly, so output never carries a failure.
- For anything that can go wrong, the author decides whether it is an error. If it is, it raises. If it isn't, the business logic handles it explicitly. For example, TMDB being down raises, while TMDB finding no match is handled.
- A failed dependency raises unless the author decided it isn't an error. The use case never hides a failure or quietly finds another way to do the job.
- Optional arguments are declared as optional, and the logic has an explicit path for when they're absent.
- A use case must be safe to run again after failing halfway.

```python
# Avoid: hiding a failure and quietly doing the job another way.
try:
    tmdb_id = await self._title_matcher.find_tmdb_id(title)
except Exception:
    return await self._create_unmatched_movie(title)

# Avoid: returning a failure as output.
if cinema is None:
    return self.OutputData(status="failed")

# Prefer: an error raises, and output means it worked.
if cinema is None:
    raise CinemaNotFoundError(f"Cinema '{cinema_id}' not found")

# Prefer: the dependency's failure propagates, and an accepted
# outcome has an explicit path in the business logic.
tmdb_id = await self._title_matcher.find_tmdb_id(title)
if tmdb_id is None:
    return await self._create_unmatched_movie(title)
```
