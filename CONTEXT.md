# Marquise

Montreal cinema showtime aggregation and management.

## Product thesis

Marquise makes relevant films and screenings in Montreal easy to discover while keeping showtime information trustworthy.

- Montreal web product first; expand only on evidence.
- Data trust is a product concern: freshness, duplicate entities, stale showtimes, timezone errors and broken links are user-facing defects.
- Prefer focused, reversible experiments over premature complexity.
- Optimize for user value, trust, retention, learning and sustainable growth.

Open assumptions: a clearly designed discovery experience reduces the effort of finding screenings, and reliable, current showtime data is a meaningful differentiator.

## Language

**Editor**:
An invited account authorized to mutate Marquise cinema catalog and showtime data.
_Avoid_: Operator, admin

**Administrator**:
An invited account authorized to administer Marquise accounts and roles and to perform Editor mutations.
_Avoid_: Admin

**Member**:
An account that may access only Marquise data owned by that account, such as preferences and saved screenings.
_Avoid_: User, customer
