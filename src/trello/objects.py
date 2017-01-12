'''
Created on 30.12.2016

@author: glorpen
'''
from trello.utils import ApiObject, api_field, simple_api_field,\
    collection_api_field, python_to_trello
import datetime
from trello.registry import events

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
    _api_object_fields = ("color","name","uses")
    
    name = simple_api_field("name")
    color = simple_api_field("color")
    uses = simple_api_field("uses", writable=False)
    
    def __repr__(self):
        return "<Label %r:%r>" % (self.name, self.color)
    
    @events.listener("label.assigned")
    def on_assigned(self, source, label, uses = None):
        if label is self and self.api_data.loaded:
            self.api_data["uses"].value = (self.uses + 1) if uses is None else uses
            self.logger.debug("Label uses counter incremented")
    
    @events.listener("label.unassigned")
    def on_unassigned(self, source, label):
        if label is self and self.api_data.loaded:
            self.api_data["uses"].value = self.uses - 1
            self.logger.debug("Label uses counter decremented")
    
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
    _api_object_fields = ("name", "pos", "idCard")
    
    def __repr__(self):
        return "<Checklist %r>" % (self.id,)
    
    name = simple_api_field("name")
    
    @api_field
    def card(self, data):
        return self._api.get_object(Card, id=data["idCard"])
    
    @collection_api_field
    def items(self, data):
        return self._fetch_objects("checklists/{id}/checkItems", Checkitem, checklist_id=self.id, card_id=self.card.id)
    
    @items.remove
    def items(self, item):
        self._api.do_request("checklists/%s/checkItems/%s" % (self.id, item.id), method="delete")
    
    @items.add
    def items(self, name, pos=None, checked=False):
        return self._fetch_object("checklists/{id}/checkItems", Checkitem, {
            "name": name,
            "pos": pos,
            "checked": "true" if checked else "false"
        }, checklist_id=self.id, card_id=self.card.id)

class Card(ApiObject):
    _api_object_url = "cards/{id}"
    _api_object_fields = ("name","desc","subscribed","closed","dueComplete","due","idAttachmentCover","idBoard", "idList")
    
    def __repr__(self):
        return "<Card %r>" % self.id
    
    name = simple_api_field("name")
    description = simple_api_field("desc")
    subscribed = simple_api_field("subscribed")
    closed = simple_api_field("closed")
    dueComplete = simple_api_field("dueComplete")
    
    due = simple_api_field("due")
    
    @api_field
    def board(self, data):
        return self._api.get_object(Board, id=data["idBoard"])
    
    @api_field
    def list(self, data):
        return self._api.get_object(List, id=data["idList"])
    
    @due.loader
    def due(self, data):
        if data['due']:
            return datetime.datetime.strptime(data['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
    
    @collection_api_field
    def attachments(self, data):
        return self._fetch_objects("cards/{id}/attachments", Attachment, card_id = self.id)
    
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
        # TODO: should add new labels to board.labels.items, change it to set() ? 
        return (self._api.get_object(Label, id=i) for i in self._do_request("cards/{id}/idLabels"))
    
    @labels.add
    def labels(self, label=None, name=None, color=None):
        uses = None
        
        if label:
            self._api.do_request("cards/%s/idLabels" % self.id, method="post", parameters={"value":label.id})
        else:
            data = self._api.do_request("cards/%s/labels" % self.id, method="post", parameters={"name":name,"color":color})
            label = self._api.get_object(Label, data=data)
            
            self._api.trigger("label.created", self, label)
            uses = label.uses
            
        self._api.trigger("label.assigned", self, label, uses)
        
        return label
    
    @labels.remove
    def labels(self, label):
        self._api.do_request("cards/%s/idLabels/%s" % (self.id, label.id), method="delete")
        self._api.trigger("label.unassigned", self, label)
    
    @events.listener("label.removed")
    def on_label_removed(self, source, subject):
        # labels are fetched together with Card data
        try:
            self.labels.items.remove(subject)
        except ValueError:
            pass
    
    @collection_api_field
    def checklists(self, data):
        return self._fetch_objects("cards/{id}/checklists", Checklist)
    
    @checklists.add
    def checklists(self, name, pos=None):
        return self._fetch_object("cards/{id}/checklists", Checklist, {
            "name": name,
            "pos": pos
        })
    
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

    # TODO board getter?
    
    @collection_api_field
    def members(self, data):
        return self._fetch_objects("cards/{id}/members", Member)
    
class List(ApiObject):
    
    _api_object_url = "lists/{id}"
    
    name = simple_api_field("name")
    position = simple_api_field("pos")
    #TODO: change other list numbers?
    
    def __repr__(self):
        return "<List %r>" % self.id
    
    @collection_api_field
    def cards(self, data):
        return self._fetch_objects("lists/{id}/cards", Card)
    
    @cards.add
    def cards(self, name, description=None, members=None, due=None):
        #TODO: name=None, card=None - when providing card, card will be moved & move event triggered
        params = {"name": name}
        
        if description:
            params["desc"] = description
        if members:
            params["idMembers"] = ",".join(i.id for i in members)
        if due:
            params["due"] = python_to_trello(due)
        
        return self._api.get_object(Card, data=self._api.do_request("lists/%s/cards" % self.id, method="post", parameters=params))
    
    @cards.remove
    def cards(self, card):
        #self._api.do_request("cards/%s" % card.id, method="delete")
        self._api.do_request("cards/%s/closed" % card.id, method="put", parameters={"value":"true"})

class Board(ApiObject):
    _api_object_url = "boards/{id}"
    _api_object_fields = ("name", "desc", "subscribed")
    
    name = simple_api_field("name")
    description = simple_api_field("desc")
    subscribed = simple_api_field("subscribed")
    
    def __repr__(self):
        return '<Board %r>' % (self.id,)
    
    @collection_api_field
    def lists(self, data):
        return self._fetch_objects("boards/{id}/lists", List)
    
    @lists.add
    def lists(self, name, pos=None):
        return self._fetch_object("boards/{id}/lists", List, {"name":name,"pos":pos})
    
    @lists.remove
    def lists(self, list):
        self._api.do_request("lists/%s/closed" % list.id, method="put", parameters={"value":'true'})
    
    @collection_api_field
    def labels(self, data):
        items = self._fetch_objects("boards/{id}/labels", Label, parameters={"limit":1000})
        # hm, there is no pagination
        if len(items) == 1000:
            self.logger.error("Label count for %r exceeds 1000 limit, adding new labels will create duplicates", self)
        return items
    
    @labels.add
    def labels(self, name, color = None):
        return self._fetch_object(Label, "boards/{id}/labels", parameters={"name":name,"color":color})
    
    @labels.remove
    def labels(self, label):
        self._api.do_request("labels/%s" % label.id, method='delete')
        self._api.trigger("label.removed", self, label)
    
    @events.listener("label.created")
    def on_label_created(self, source, label):
        if source is self:
            return
        if self.get_api_field_data("labels").loaded:
            if label not in self.labels.items:
                self.labels.items.append(label)
    
    @collection_api_field
    def members(self, data):
        return self._fetch_objects("board/{id}/members", Member)
    
class Notification(ApiObject):
    _api_object_url = "notifications/{id}"
    
    ADDED_TO_BOARD = 'addedToBoard'
    CREATED_CARD = 'createdCard'
    
    type = simple_api_field("type", writable=False)
    unread = simple_api_field("unread")
    
    @api_field
    def card(self, data):
        if "card" in data["data"]:
            return self._api.get_object(Card, id=data["data"]["card"]["id"])
    
    @api_field
    def board(self, data):
        if "board" in data["data"]:
            return self._api.get_object(Board, id=data["data"]["board"]["id"])
    
    @api_field
    def list(self, data):
        if "list" in data["data"]:
            return self._api.get_object(Board, id=data["data"]["list"]["id"])
    
    def read(self):
        self.unread = False

class Member(ApiObject):
    _api_object_url = "members/{id}"
    _api_object_fields = ("email","username","fullName","url")
    
    email = simple_api_field("email", writable=False)
    username = simple_api_field("username")
    full_name = simple_api_field("fullName")
    url = simple_api_field("url", writable=False)
    
    @collection_api_field
    def boards(self, data):
        return self._fetch_objects("members/{id}/boards", Board)
    
    @collection_api_field
    def cards(self, data):
        return self._fetch_objects("members/{id}/cards", Card)
    
    @collection_api_field
    def notifications(self, data):
        return self._fetch_objects("members/{id}/notifications", Notification)
    