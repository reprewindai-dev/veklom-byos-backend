## 2024-05-24 - Async HTTP Health Checks
**Learning:** Sequential HTTP requests in backend monitoring routes can cause significant blocking latency (up to 10s worst-case for 5 services). Since these are external requests, they don't lock the SQLAlchemy session and can be safely parallelized.
**Action:** Use `asyncio.gather` for independent external network calls in backend routes to bound latency to the single slowest request.
