=============================
Grello - a Trello API library
=============================

Simple objects with lazy load
=============================

Automatic ID updating
=====================

When fetching fresh data from API, objects can have its id changed.

If given object had id as *short id* (in eg. Card objects), *alias* (eg. "token/me") or other fields supported by Trello API,
data returned by API would have real id and so the id fields of object will be changed to new value.
