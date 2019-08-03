========================================
Grello - a python library for Trello API
========================================

Grello allows to easly interact with the Trello API.

This library is based on Trello API documentation: https://developers.trello.com/advanced-reference.

Simple objects with lazy load
=============================

Tracking object states
======================

Library tries to make as few api requests as it can, so for example creating Label on given Board by
board.labels.add(name="some_name") will automatically add created label object to labels list,
so fetching another list of board.labels is not needed.
More advanced example is adding or removing Label from Card, this actions will change counter of given Label
without querying Trello servers.

Library is assuming that no third party modifications are taking place during its operation.

Automatic ID updating
=====================

When fetching fresh data from Trello, objects can have its id changed if given id is a alias or shortcut.

If given object had id as *short id* (in eg. Card objects), *alias* (eg. "token/me") or other fields supported by Trello API,
data returned by API would have real id and so the id fields of object will be changed to new value.

Example:

.. sourcecode: python

   a = Api("xxxxxxxxxxxxx", Ui())
   a.connect("xxxxxxxxxxxxxxxxxxx")
   m = a.get_any(Member, id="me")
   print(m.id)
   print(m.email) # access to not loaded property will trigger object load
   print(m.id)

Will print:

..

   me
   example@example.com
   xxxx9028b29xxf71g236fbxx

Filtered lists
==============

To control scope of fetched lists you can use additional arguments in call method.

.. sourcecode:: python

   len(some_list.cards) # default list "visible"
   len(some_list.cards(filter=Card.FILTER_ALL)) # all cards - visible and closed
