'''
Created on 30.12.2016

@author: glorpen
'''
from trello.utils import ApiObject, api_field, simple_api_field,\
    collection_api_field

class Attachment(ApiObject):
    
    _id_fields = {"id":"id", "cardId":"card_id"}
    
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
    
    def _get_data_url(self):
        return "labels/%s" % (self.id,)
    
    name = simple_api_field("name")
    color = simple_api_field("color")
    
    def __repr__(self):
        return "<Label %r:%r>" % (self.name, self.color)

class Card(ApiObject):
    def _get_data_url(self):
        return "cards/%s" % self.id
    
    name = simple_api_field("name")
    description = simple_api_field("desc")
    subscribed = simple_api_field("subscribed")
    
    @collection_api_field
    def attachments(self, data):
        a = tuple(Attachment(card_id = self.id, data=i, api=self._api) for i in self._api.do_request("cards/%s/attachments" % self.id))
        
        cover_id = self.cover.id if self.cover else None
        if cover_id:
            return filter(lambda x: x.id != cover_id, a)
        else:
            return a
    
    @collection_api_field
    def labels(self, data):
        return (Label(data=i, api=self._api) for i in data["labels"])
    
    @labels.add
    def labels(self, label):
        self._api.do_request("cards/%s/idLabels" % self.id, method="post", parameters={"value":label.id})
    
    
    @api_field
    def cover(self, data):
        cover_id = data["idAttachmentCover"]
        if cover_id:
            return Attachment(card_id = self.id, id = cover_id, api=self._api)
    
    @cover.setter
    def cover(self, value):
        #if attachement id on this card? - change cover id
        #is from diffrent card? - copy
        #is path from disk - upload
        print(value)
        # update attachments collection in this object
    
        
    
class List(ApiObject):
    
    name = simple_api_field("name")
    
    def __repr__(self):
        return "<List %r>" % self.id
    
    def _get_data_url(self):
        return "lists/%s" % self.id
    
    def get_cards(self):
        return tuple(Card(data=i, api=self._api) for i in self._api.do_request("lists/%s/cards" % self.id))

class Board(ApiObject):
    def _get_data_url(self):
        return "boards/%s" % self.id
    
    def __repr__(self):
        return '<Board %r>' % (self.id,)
    
    def get_lists(self):
        return tuple(List(data=i, api=self._api) for i in self._api.do_request("boards/%s/lists" % self.id))
    
    def get_labels(self):
        return tuple(Label(data=i, api=self._api) for i in self._api.do_request("boards/%s/labels" % self.id))
    
    def create_label(self, name, color = None):
        return Label(
            data=self._api.do_request("boards/%s/labels" % self.id, method='post', parameters={"name":name,"color":color}),
            api=self._api
        )
