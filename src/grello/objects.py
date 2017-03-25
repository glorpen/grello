'''
Created on 30.12.2016

@author: glorpen
'''
from grello.utils import python_to_trello, Logger
from grello.fields import api_field, simple_api_field, collection_api_field
import datetime
from grello.registry import events, api_object

@api_object(
    url = "cards/{card_id}/attachments/{id}"
)
class Attachment(object):
    def __repr__(self):
        return "<Attachment %r in card %r>" % (self.id, self.card_id)
    
    name = simple_api_field("name", writable=False)
    mime_type = simple_api_field("mimeType", writable=False)
    url = simple_api_field("url", writable=False)
    size = simple_api_field("bytes", writable=False)

@api_object(
    url = "labels/{id}",
    default_fields = ("color","name","uses")
)
class Label(Logger):
    
    RED = 'red'
    GREEN = 'green'
    YELLOW = 'yellow'
    ORANGE = 'orange'
    BLUE = 'blue'
    PURPLE = 'purple'
    BLACK = 'black'
    
    NO_COLOR = None
    
    name = simple_api_field("name")
    color = simple_api_field("color")
    uses = simple_api_field("uses", writable=False)
    
    def __repr__(self):
        return "<Label %r:%r>" % (self.name, self.color)
    
    @events.listener("label.assigned")
    def on_assigned(self, api_data, source, label, uses = None):
        if label is self and api_data.loaded:
            api_data.get_field("uses").value = (self.uses + 1) if uses is None else uses
            self.logger.debug("Label uses counter incremented")
    
    @events.listener("label.unassigned")
    def on_unassigned(self, api_data, source, label):
        if label is self and api_data.loaded:
            api_data.get_field("uses").value = self.uses - 1
            self.logger.debug("Label uses counter decremented")

@api_object(
    url = "cards/{card_id}/checklist/{checklist_id}/checkItem/{id}",
    default_fields = ("name", "pos", "state")
)
class Checkitem(object):
    COMPLETE = 'complete'
    INCOMPLETE = 'incomplete'
    
    def __repr__(self):
        return "<Checkitem %r from checklist %r>" % (self.id, self.checklist_id)
    
    name = simple_api_field("name")
    state = simple_api_field("state")
    position = simple_api_field("pos")
    
    completed = simple_api_field("state")
    
    @completed.loader
    def completed(self, data):
        return data["state"] == self.COMPLETE

@api_object(
    url = "checklists/{id}",
    default_fields = ("name", "pos", "idCard")
)
class Checklist(object):
    
    def __repr__(self):
        return "<Checklist %r>" % (self.id,)
    
    name = simple_api_field("name")
    
    @api_field
    def card(self, data, repository):
        return repository.get_object(Card, id=data["idCard"])
    
    @collection_api_field
    def items(self, data, api_data):
        return api_data.fetch_objects("checklists/{id}/checkItems", Checkitem, checklist_id=self.id, card_id=self.card.id)
    
    @items.remove
    def items(self, connection, item):
        connection.do_request("checklists/%s/checkItems/%s" % (self.id, item.id), method="delete")
    
    @items.add
    def items(self, api_data, name, pos=None, checked=False):
        return api_data.fetch_object("checklists/{id}/checkItems", Checkitem, {
            "name": name,
            "pos": pos,
            "checked": "true" if checked else "false"
        }, checklist_id=self.id, card_id=self.card.id)

@api_object(
    url = "cards/{id}",
    default_fields = ("name","desc","subscribed","closed","dueComplete","due","idAttachmentCover","idBoard", "idList")
)
class Card(object):
    
    def __repr__(self):
        return "<Card %r>" % self.id
    
    name = simple_api_field("name")
    description = simple_api_field("desc")
    subscribed = simple_api_field("subscribed")
    closed = simple_api_field("closed")
    dueComplete = simple_api_field("dueComplete")
    
    due = simple_api_field("due")
    
    @api_field
    def board(self, data, repository):
        return repository.get_object(Board, id=data["idBoard"])
    
    @api_field
    def list(self, data, repository):
        return repository.get_object(List, id=data["idList"])
    
    @due.loader
    def due(self, data):
        if data['due']:
            return datetime.datetime.strptime(data['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
    
    @collection_api_field
    def attachments(self, data, api_data):
        return api_data.fetch_objects("cards/{id}/attachments", Attachment, card_id = self.id)
    
    @attachments.add
    def attachments(self, connection, repository, file=None, name=None, url=None, mime_type=None):
        ret = connection.do_request(
            "cards/%s/attachments" % self.id,
            method="post",
            parameters={
                "name": name,
                "url": url,
                "mimeType": mime_type
            },
            files={"file": file}
        )
        
        return repository.get_object(Attachment, card_id=self.id, data=ret)
    
    @collection_api_field
    def labels(self, data, api_data, repository):
        # TODO: should add new labels to board.labels.items, change it to set() ? 
        return (repository.get_object(Label, id=i) for i in api_data.do_request("cards/{id}/idLabels"))
    
    @labels.add
    def labels(self, connection, repository, event_dispatcher, label=None, name=None, color=None):
        uses = None
        
        if label:
            connection.do_request("cards/%s/idLabels" % self.id, method="post", parameters={"value":label.id})
        else:
            data = connection.do_request("cards/%s/labels" % self.id, method="post", parameters={"name":name,"color":color})
            label = repository.get_object(Label, data=data)
            
            event_dispatcher.trigger("label.created", self, label)
            uses = label.uses
            
        event_dispatcher.trigger("label.assigned", self, label, uses)
        
        return label
    
    @labels.remove
    def labels(self, connection, event_dispatcher, label):
        connection.do_request("cards/%s/idLabels/%s" % (self.id, label.id), method="delete")
        event_dispatcher.trigger("label.unassigned", self, label)
    
    @events.listener("label.removed")
    def on_label_removed(self, source, subject):
        # labels are fetched together with Card data
        try:
            self.labels.items.remove(subject)
        except ValueError:
            pass
    
    @collection_api_field
    def checklists(self, data, api_data):
        return api_data.fetch_objects("cards/{id}/checklists", Checklist)
    
    @checklists.add
    def checklists(self, api_data, name, pos=None):
        return api_data.fetch_object("cards/{id}/checklists", Checklist, {
            "name": name,
            "pos": pos
        })
    
    @checklists.remove
    def checklists(self, connection, checklist):
        connection.do_request("checklists/%s" % (checklist.id,), method="delete")
    
    @api_field
    def cover(self, data, repository):
        cover_id = data["idAttachmentCover"]
        if cover_id:
            return repository.get_object(Attachment, card_id = self.id, id = cover_id)
    
    @cover.setter
    def cover(self, connection, attachment):
        connection.do_request("cards/%s/idAttachmentCover" % self.id, method="put", parameters={"value": attachment.id})

    # TODO board getter?
    
    @collection_api_field
    def members(self, data, api_data):
        return api_data.fetch_objects("cards/{id}/members", Member)

@api_object(
    url = "lists/{id}"
)
class List(object):
    
    name = simple_api_field("name")
    position = simple_api_field("pos")
    #TODO: change other list numbers?
    
    def __repr__(self):
        return "<List %r>" % self.id
    
    @collection_api_field
    def cards(self, data, api_data):
        return api_data.fetch_objects("lists/{id}/cards", Card)
    
    @cards.add
    def cards(self, repository, connection, name, description=None, members=None, due=None):
        #TODO: name=None, card=None - when providing card, card will be moved & move event triggered
        params = {"name": name}
        
        if description:
            params["desc"] = description
        if members:
            params["idMembers"] = ",".join(i.id for i in members)
        if due:
            params["due"] = python_to_trello(due)
        
        return repository.get_object(Card, data=connection.do_request("lists/%s/cards" % self.id, method="post", parameters=params))
    
    @cards.remove
    def cards(self, connection, card):
        #self._api.do_request("cards/%s" % card.id, method="delete")
        connection.do_request("cards/%s/closed" % card.id, method="put", parameters={"value":"true"})

@api_object(
    url = "boards/{id}",
    default_fields = ("name", "desc", "subscribed")
)
class Board(Logger):
    
    name = simple_api_field("name")
    description = simple_api_field("desc")
    subscribed = simple_api_field("subscribed")
    
    def __repr__(self):
        return '<Board %r>' % (self.id,)
    
    @collection_api_field
    def lists(self, data, api_data):
        return api_data.fetch_objects("boards/{id}/lists", List)
    
    @lists.add
    def lists(self, api_data, name, pos=None):
        return api_data.fetch_object("boards/{id}/lists", List, {"name":name,"pos":pos})
    
    @lists.remove
    def lists(self, connection, list):
        connection.do_request("lists/%s/closed" % list.id, method="put", parameters={"value":'true'})
    
    @collection_api_field
    def labels(self, data, api_data):
        items = api_data.fetch_objects("boards/{id}/labels", Label, parameters={"limit":1000})
        # hm, there is no pagination
        if len(items) == 1000:
            self.logger.error("Label count for %r exceeds 1000 limit, adding new labels will create duplicates", self)
        return items
    
    @labels.add
    def labels(self, api_data, name, color = None):
        return api_data.fetch_object("boards/{id}/labels", Label, {"name":name,"color":color})
    
    @labels.remove
    def labels(self, connection, event_dispatcher, label):
        connection.do_request("labels/%s" % label.id, method='delete')
        event_dispatcher.trigger("label.removed", self, label)
    
    @events.listener("label.created")
    def on_label_created(self, api_data, source, label):
        if source is self:
            return
        if api_data.get_field("labels").loaded:
            if label not in self.labels.items:
                self.labels.items.append(label)
    
    @collection_api_field
    def members(self, data, api_data):
        return api_data.fetch_objects("board/{id}/members", Member)
    
@api_object(
    url = "notifications/{id}"
)
class Notification(object):
    
    ADDED_TO_BOARD = 'addedToBoard'
    CREATED_CARD = 'createdCard'
    CHANGED_CARD = 'changeCard'
    
    type = simple_api_field("type", writable=False)
    unread = simple_api_field("unread")
    
    @api_field
    def card(self, data, repository):
        if "card" in data["data"]:
            return repository.get_object(Card, id=data["data"]["card"]["id"])
    
    @api_field
    def board(self, data, repository):
        if "board" in data["data"]:
            return repository.get_object(Board, id=data["data"]["board"]["id"])
    
    @api_field
    def list(self, data, repository):
        if "list" in data["data"]:
            return repository.get_object(List, id=data["data"]["list"]["id"])
    
    def read(self):
        self.unread = False

@api_object(
    url = "members/{id}",
    default_fields = ("email","username","fullName","url")
)
class Member(object):
    
    email = simple_api_field("email", writable=False)
    username = simple_api_field("username")
    full_name = simple_api_field("fullName")
    url = simple_api_field("url", writable=False)
    
    @collection_api_field
    def boards(self, data, api_data):
        return api_data.fetch_objects("members/{id}/boards", Board)
    
    @collection_api_field
    def cards(self, data, api_data):
        return api_data.fetch_objects("members/{id}/cards", Card)
    
    @collection_api_field
    def notifications(self, data, api_data):
        return api_data.fetch_objects("members/{id}/notifications", Notification)
    