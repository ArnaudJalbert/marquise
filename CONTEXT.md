# Marquise

Montreal cinema showtime aggregation and management.

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

**Bot**:
A non-human account that calls protected Marquise API endpoints.
_Avoid_: Script, automation

**Bot Identifier**:
An immutable, unique lowercase slug identifying a Bot account.
_Avoid_: Bot name
