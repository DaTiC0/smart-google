## 2024-05-18 - [Fix N+1 query]
**Learning:** Fixed N+1 queries in `rstate` and `onQuery` by bulk fetching data instead of using `rquery` inside a loop.
**Action:** Always check for repeated fetches in loops that can be optimized to a bulk fetch.
