========================================
Grello - a python library for Trello API
========================================

Grello allows to easly interact with the Trello API.

This library is based on Trello API documentation: https://developers.trello.com/advanced-reference.

Simple objects with lazy load
=============================

Tracking object states
======================

Automatic ID updating
=====================

When fetching fresh data from API, objects can have its id changed.

If given object had id as *short id* (in eg. Card objects), *alias* (eg. "token/me") or other fields supported by Trello API,
data returned by API would have real id and so the id fields of object will be changed to new value.
