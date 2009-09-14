import logging
import uuid

from django.db import models
from django.contrib.auth.models import User
import django.db.models.signals as signals
from django.http import HttpResponse
from django.core.urlresolvers import reverse

from bookworm.library import models as bookworm_models
from bookworm.api import APIException

log = logging.getLogger(__name__)

class APIKeyManager(models.Manager):
    '''Override some default creation methods to automatically generate a key'''

    def create(self, **kwargs):
        '''Override the basic create method'''
        qs = self.get_query_set().create(**kwargs)
        qs.key = self.generate_key()
        qs.save()
        return qs
    
    def get_or_create(self, **kwargs):
        '''Override get_or_create to create a new key if the user doesn't already exist, or to just
        return the existing one if it already is in the database.'''
        (qs, created) = self.get_query_set().get_or_create(**kwargs)
        if created:
            qs.key = self.generate_key()
            qs.save()
        return (qs, created)
    
    def generate_key(self):
        '''Generates an API key as a 32-character hex UUID'''
        return uuid.uuid4().hex

    def is_valid(self, key, user):
        '''Assert whether a key is valid (matches the value in the database) for a particular user'''
        try:
            apikey = self.get(user=user)
        except APIKey.DoesNotExist:
            raise APIException("No matching user %s has an API key" % user)
        return apikey.key == key
    
    def user_for_key(self, key):
        '''Return the user object for this key, or an APIException if no key matches'''
        try:
            apikey = self.get(key=key)
        except APIKey.DoesNotExist:
            raise APIException("No matching key for %s" % key)
        return apikey.user
        
       
class APIKey(bookworm_models.BookwormModel):
    '''Stores the user's current API key'''
    user = models.ForeignKey(User, unique=True)
    key = models.CharField(max_length=32, unique=True)
    objects = APIKeyManager()

    def is_valid(self, key):
        '''Assert whether a key is valid (matches the value in the database)'''
        return self.key == key

    def __unicode__(self):
        return u"API key %s for %s (%s)" % (self.key, self.user.username, self.user.email)
    
def update_api_key(sender, instance, **kwargs):
    '''Signal handler to update the user's API key if the username or password has changed'''
    # Get a copy of the user object as it exists in the database
    try:
        user = User.objects.get(id=instance.id)
    except User.DoesNotExist:
        return
    if user.username != instance.username or user.password != instance.password:
        apikey = APIKey.objects.get_or_create(user=user)[0]
        apikey.key = APIKey.objects.generate_key()
        apikey.save()
        
signals.pre_save.connect(update_api_key, sender=User, weak=False)
