'''
Created on 30.12.2016

@author: glorpen
'''
from trello.utils import ApiObject, api_field, simple_api_field,\
    collection_api_field, api_listener
import datetime

# TOOD: remove label from event_bus when label is removed


class Attachment(ApiObject):
    
    _api_id_fields = ("id", "card_id")
    _api_object_url = "cards/{card_id}/attachments/{id}"
    
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
    
    _api_object_url = "labels/{id}"
    
    name = simple_api_field("name")
    color = simple_api_field("color")
    uses = simple_api_field("uses", writable=False)
    
    def __repr__(self):
        return "<Label %r:%r>" % (self.name, self.color)
    
    @api_listener("label.assigned")
    def on_assigned(self, label, uses = None):
        if label is self and self.is_loaded:
            self.get_api_field_data("uses").value = (self.uses + 1) if uses is None else uses
            self.logger.debug("Label uses counter incremented")
    
    @api_listener("label.unassigned")
    def on_unassigned(self, label):
        if label is self and self.is_loaded:
            self.get_api_field_data("uses").value = self.uses - 1
            self.logger.debug("Label uses counter decremented")
    
    @api_listener("label.removed")
    def on_removed(self, label):
        if label is self:
            self._api.event_bus.unsubscribe(self)
    
class Checkitem(ApiObject):
    _api_id_fields = ("id", "checklist_id", "card_id")
    
    COMPLETE = 'complete'
    INCOMPLETE = 'incomplete'
    
    _api_object_url = "cards/{card_id}/checklist/{checklist_id}/checkItem/{id}"
    
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
    _api_object_url = "checklists/{id}"
    
    def __repr__(self):
        return "<Checklist %r>" % (self.id,)
    
    name = simple_api_field("name")
    
    @api_field
    def card(self, data):
        return self._api.get_object(Card, id=data["idCard"])
    
    @collection_api_field
    def items(self, data):
        return (self._api.get_objects(Checkitem, data=data["checkItems"], checklist_id=self.id, card_id=self.card.id))
    
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
        
        return self._api.get_object(Checkitem, data=ret, checklist_id=self.id, card_id=self.card.id)

class Card(ApiObject):
    _api_object_url = "cards/{id}"
    
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
    
    @collection_api_field(always_fresh=True)
    def attachments(self, data):
        return (self._api.get_objects(Attachment, card_id = self.id, data=self._api.do_request("cards/%s/attachments" % self.id)))
    
    @attachments.add
    def attachments(self, file=None, name=None, url=None, mime_type=None):
        ret = self._api.do_request("cards/%s/attachments" % self.id, method="post", parameters={
            "file": file,
            "name": name,
            "url": url,
            "mimeType": mime_type
        })
        
        return self._api.get_object(Attachment, card_id=self.id, data=ret)
    
    @collection_api_field
    def labels(self, data):
        return (self._api.get_objects(Label, data=data["labels"]))
    
    @labels.add
    def labels(self, label=None, name=None, color=None):
        uses = None
        
        if label:
            self._api.do_request("cards/%s/idLabels" % self.id, method="post", parameters={"value":label.id})
        else:
            data = self._api.do_request("cards/%s/labels" % self.id, method="post", parameters={"name":name,"color":color})
            label = self._api.get_object(Label, data=data)
            
            self._api.event_bus.trigger("label.created", label)
            uses = label.uses
            
        self._api.event_bus.trigger("label.assigned", label, uses)
        
        return label
    
    @labels.remove
    def labels(self, label):
        self._api.do_request("cards/%s/idLabels/%s" % (self.id, label.id), method="delete")
        self._api.event_bus.trigger("label.unassigned", label)
    
    @api_listener("label.removed")
    def on_label_removed(self, label):
        if self.get_api_field_data("labels").loaded:
            try:
                self.labels.remove(label)
            except ValueError:
                pass
    
    @collection_api_field
    def checklists(self, data):
        return (self._api.get_object(Checklist, id=i) for i in data["idChecklists"])
    
    @checklists.add
    def checklists(self, name, pos=None):
        data = self._api.do_request("cards/%s/checklists" % (self.id,), method="post", parameters={
            "name": name,
            "pos": pos
        })
        return self._api.get_object(Checklist, data=data, card_id=self.id)
    
    @checklists.remove
    def checklists(self, checklist):
        self._api.do_request("checklists/%s" % (checklist.id,), method="delete")
    
    @api_field
    def cover(self, data):
        cover_id = data["idAttachmentCover"]
        if cover_id:
            return self._api.get_object(Attachment, card_id = self.id, id = cover_id)
    
    @cover.setter
    def cover(self, attachment):
        self._api.do_request("cards/%s/idAttachmentCover" % self.id, method="put", parameters={"value": attachment.id})

    #todo: board getter?
    
class List(ApiObject):
    
    _api_object_url = "lists/{id}"
    
    name = simple_api_field("name")
    
    def __repr__(self):
        return "<List %r>" % self.id
    
    @collection_api_field(always_fresh=True)
    def cards(self, data):
        return (self._api.get_objects(Card, data=self._api.do_request("lists/%s/cards" % self.id)))

class Board(ApiObject):
    _api_object_url = "boards/{id}"
    
    def __repr__(self):
        return '<Board %r>' % (self.id,)
    
    @collection_api_field(always_fresh=True)
    def lists(self, data):
        return self._api.get_objects(List, data=self._api.do_request("boards/%s/lists" % self.id))
    
    @collection_api_field(always_fresh=True)
    def labels(self, data):
        items = tuple(self._api.get_objects(Label, data=self._api.do_request("boards/%s/labels" % self.id, parameters={"limit":1000})))
        # hm, there is no pagination
        if len(items) == 1000:
            self.logger.error("Label count for %r exceeds 1000 limit, adding new labels will create duplicates", self)
        return items
    
    @labels.add
    def labels(self, name, color = None):
        return self._api.get_object(Label,
            data=self._api.do_request("boards/%s/labels" % self.id, method='post', parameters={"name":name,"color":color})
        )
    
    @labels.remove
    def labels(self, label):
        self._api.do_request("labels/%s" % label.id, method='delete')
        self._api.event_bus.trigger("label.removed", label)
    
    @api_listener("label.created")
    def on_label_created(self, label):
        if self.get_api_field_data("labels").loaded:
            if label not in self.labels.items:
                self.labels.items.append(label)
