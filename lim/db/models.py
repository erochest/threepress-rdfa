from google.appengine.ext import db
from google.appengine.api import users
from datetime import datetime
from urllib import quote_plus, unquote_plus

# Functions
def safe_name(name):
    return quote_plus(name)

def unsafe_name(name):
    return unquote_plus(name)

def english_date(date):
    return date

def english_date_diff(date):
    d = date - datetime.now()
    if d.days == 0:
        return '%d hours ago' % d.hours
    if d.days == -1:
        return 'yesterday'
    if d.days > -6:
        return '%d days ago' % abs(d.days)
    if d.days == -7:
        return 'one week ago'
    return english_date(date)


# Properties
class Priority(db.Property):
    def __init__(self, 
                 verbose_name='priority', 
                 choices=('high', 'medium', 'low'),
                 **kwds):
        super(Priority, self).__init__(verbose_name, choices, **kwds)

class BugStatus (db.StringProperty):
    def __init__(self, 
                 verbose_name='status', 
                 choices=('fixed', 'open', 'duplicate', 'enhancement', 'unreproducible'),
                 **kwds):
        super(BugStatus, self).__init__(verbose_name, choices, **kwds)


# Models
class LimBase(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    def english_created(self):
        return english_date(self.created)
    def english_last_modified(self):
        return english_date_diff(self.last_modified)

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
    client = db.ReferenceProperty(Client)

class Bug(LimBase):
    bug_num = db.IntegerProperty()
    title = db.StringProperty(required=True)
    description = db.TextProperty()
    creator = db.UserProperty()
    project = db.ReferenceProperty(Project)

    def safe_name(self):
        return safe_name(self.title)    

class BugState(LimBase):
    owner = db.UserProperty()    
    message = db.TextProperty()
    priority = db.StringProperty()
    status = BugStatus()
    bug = db.ReferenceProperty(Bug)

