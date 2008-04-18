from google.appengine.ext import db
from google.appengine.api import users
from datetime import *

# Functions
def unsafe_name(name):
    return name.replace('_', ' ')

def safe_name(name):
    return name.replace(' ', '_')    

def english_date(date):
    d = date - datetime.now()
    from_now = datetime.now() - d 
    return from_now.isoweekday()

# Properties
class Priority(db.Property):
    def __init__(self, 
                 verbose_name='priority', 
                 choices=('high', 'medium', 'low'),
                 **kwds):
        super(Priority, self).__init__(verbose_name, choices, **kwds)

# Models
class LimBase(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    def english_created(self):
        return english_date(self.created)
    def english_last_modified(self):
        return english_date(self.last_modified)

class Lim(LimBase):

    def safe_name(self):
        return safe_name(self.name)
    def unsafe_name(self, name):
        return unsave_name(name)


class Client(Lim):
    name = db.StringProperty(required=True)
    description = db.TextProperty()
    creator = db.UserProperty()

class Project(Lim):
    name = db.StringProperty(required=True)
    description = db.TextProperty()
    creator = db.UserProperty()

class BugState(LimBase):
    owner = db.UserProperty()    
    message = db.TextProperty()
    priority = db.StringProperty()

class Bug(LimBase):
    title = db.StringProperty(required=True)
    description = db.TextProperty()
    creator = db.UserProperty()
    state = db.ReferenceProperty(BugState)
    project = db.ReferenceProperty(Project)

    def safe_name(self):
        return safe_name(self.title)    
