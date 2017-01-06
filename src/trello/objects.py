'''
Created on 30.12.2016

@author: glorpen
'''
from trello.utils import ApiObject, api_field, simple_api_field,\
    collection_api_field
import datetime

# TODO: usunięcie label z board powinno automatycznie usunąć label z załadowanych kart
# TODO: collection powinno sie przełðaować jeśli data["collectionIds"] są inne, jeśli zaciągane z urla to nie

class Attachment(ApiObject):
    
    _api_id_fields = ("id", "card_id")
    
    def _get_data_url(self):
        return "cards/%s/attachments/%s" % (self.card_id, self.id)
    
    def __repr__(self):
        return "<Attachment %r in card %r>" % (self.id, self.card_id)
    
    name = simple_api_field("name", writable=False)

class Label(ApiObject):
    
    RED = 'red'
    GREEN = 'green'
    YELLOW = 'yellow'
    ORANGE = 'orange'
    BLUE = 'blue'
    PURPLE = 'purple'
    BLACK = 'black'
    
    NO_COLOR = None
    
    def _get_data_url(self):
        return "labels/%s" % (self.id,)
    
    name = simple_api_field("name")
    color = simple_api_field("color")
    uses = simple_api_field("uses", writable=False)
    
    def __repr__(self):
        return "<Label %r:%r>" % (self.name, self.color)
    
    def _increment_uses(self):
        if self.is_loaded:
            self.get_api_field_data("uses").value = self.uses + 1
            
    def _decrement_uses(self):
        if self.is_loaded:
            self.get_api_field_data("uses").value = self.uses - 1
    
class Checkitem(ApiObject):
    _api_id_fields = ("id", "checklist_id", "card_id")
    
    COMPLETE = 'complete'
    INCOMPLETE = 'incomplete'
    
    def _get_data_url(self):
        return "cards/%s/checklist/%s/checkItem/%s" % (self.card_id, self.checklist_id, self.id)
    
    def __repr__(self):
        return "<Checkitem %r from checklist %r>" % (self.id, self.checklist_id)
    
    name = simple_api_field("name")
    state = simple_api_field("state")
    position = simple_api_field("pos")
    
    completed = simple_api_field("state")
    
    @completed.loader
    def completed(self, data):
        return data["state"] == self.COMPLETE

class Checklist(ApiObject):
    def _get_data_url(self):
        return "checklists/%s" % self.id
    
    def __repr__(self):
        return "<Checklist %r>" % (self.id,)
    
    name = simple_api_field("name")
    
    @api_field
    def card(self, data):
        return Card(id=data["idCard"], api=self._api)
    
    @collection_api_field
    def items(self, data):
        return (Checkitem(data=i, api=self._api, checklist_id=self.id, card_id=self.card.id) for i in data["checkItems"])
    
    @items.remove
    def items(self, item):
        self._api.do_request("checklists/%s/checkItems/%s" % (self.id, item.id), method="delete")
    
    @items.add
    def items(self, name, pos=None, checked=False):
        ret = self._api.do_request("checklists/%s/checkItems" % (self.id,), method="post", parameters={
            "name": name,
            "pos": pos,
            "checked": "true" if checked else "false"
        })
        
        return Checkitem(data=ret, checklist_id=self.id, card_id=self.card.id, api=self._api)

class Card(ApiObject):
    def _get_data_url(self):
        return "cards/%s" % self.id
    
    def __repr__(self):
        return "<Card %r>" % self.id
    
    name = simple_api_field("name")
    description = simple_api_field("desc")
    subscribed = simple_api_field("subscribed")
    closed = simple_api_field("closed")
    dueComplete = simple_api_field("dueComplete")
    
    due = simple_api_field("due")
    
    @due.loader
    def due(self, data):
        if data['due']:
            return datetime.datetime.strptime(data['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
    
    @collection_api_field
    def attachments(self, data):
        return (Attachment(card_id = self.id, data=i, api=self._api) for i in self._api.do_request("cards/%s/attachments" % self.id))
    
    @attachments.add
    def attachments(self, file=None, name=None, url=None, mime_type=None):
        ret = self._api.do_request("cards/%s/attachments" % self.id, method="post", parameters={
            "file": file,
            "name": name,
            "url": url,
            "mimeType": mime_type
        })
        
        return Attachment(card_id=self.id, data=ret, api=self._api)
    
    @collection_api_field
    def labels(self, data):
        return (Label(data=i, api=self._api) for i in data["labels"])
    
    @labels.add
    def labels(self, label):
        self._api.do_request("cards/%s/idLabels" % self.id, method="post", parameters={"value":label.id})
        label._increment_uses()
        return label
    
    @labels.remove
    def labels(self, label):
        label._decrement_uses()
        self._api.do_request("cards/%s/idLabels/%s" % (self.id, label.id), method="delete")
    
    @collection_api_field
    def checklists(self, data):
        return (Checklist(id=i, api=self._api) for i in data["idChecklists"])
    
    @checklists.add
    def checklists(self, name, pos=None):
        data = self._api.do_request("cards/%s/checklists" % (self.id,), method="post", parameters={
            "name": name,
            "pos": pos
        })
        return Checklist(data=data, api=self._api, card_id=self.id)
    
    @checklists.remove
    def checklists(self, checklist):
        self._api.do_request("checklists/%s" % (checklist.id,), method="delete")
    
    @api_field
    def cover(self, data):
        cover_id = data["idAttachmentCover"]
        if cover_id:
            return Attachment(card_id = self.id, id = cover_id, api=self._api)
    
    @cover.setter
    def cover(self, attachment):
        self._api.do_request("cards/%s/idAttachmentCover" % self.id, method="put", parameters={"value": attachment.id})

    #todo: board getter?
    
class List(ApiObject):
    
    name = simple_api_field("name")
    
    def __repr__(self):
        return "<List %r>" % self.id
    
    def _get_data_url(self):
        return "lists/%s" % self.id
    
    @collection_api_field
    def cards(self, data):
        return (Card(data=i, api=self._api) for i in self._api.do_request("lists/%s/cards" % self.id))

class Board(ApiObject):
    def _get_data_url(self):
        return "boards/%s" % self.id
    
    def __repr__(self):
        return '<Board %r>' % (self.id,)
    
    @collection_api_field
    def lists(self, data):
        return (List(data=i, api=self._api) for i in self._api.do_request("boards/%s/lists" % self.id))
    
    @collection_api_field
    def labels(self, data):
        items = tuple(Label(data=i, api=self._api) for i in self._api.do_request("boards/%s/labels" % self.id, parameters={"limit":1000}))
        # hm, there is no pagination
        if len(items) == 1000:
            self.logger.error("Label count for %r exceeds 1000 limit, adding new labels will create duplicates", self)
        return items
    
    @labels.add
    def labels(self, name, color = None):
        return Label(
            data=self._api.do_request("boards/%s/labels" % self.id, method='post', parameters={"name":name,"color":color}),
            api=self._api
        )
    
    @labels.remove
    def labels(self, label):
        self._api.do_request("labels/%s" % label.id, method='delete')
