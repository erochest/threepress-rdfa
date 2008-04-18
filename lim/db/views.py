# Create your views here.
from django.http import *
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.core.exceptions import *
from django.newforms import *
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError
from django.core.urlresolvers import reverse
from google.appengine.ext import db
from google.appengine.api import users
from models import *
import os.path

def get_project_from_name(name):
    return Project.gql("WHERE name = :name", name=unsafe_name(name)).get()

def get_client_from_name(name):
    return Client.gql("WHERE name = :name", name=unsafe_name(name)).get()
    
def index(request):
    projects = Project.all()
    clients = Client.all()
    user = users.get_current_user()
    if not user:
      greeting = ("<a href=\"%s\">Sign in or register</a>." %
                  users.create_login_url("/"))
      return render_to_response('login.html',  {'greeting': greeting})

    return render_to_response('index.html', {'projects':projects,
                                             'clients':clients})


def view_project(request, client_name, project_name):
    project = get_project_from_name(project_name)
    client = get_client_from_name(client_name)
    clients = Client.all()
    # Get all bugs
    bugs = Bug.gql("WHERE project = :project ORDER BY created DESC", project=project)
    return render_to_response('projects/view.html', 
                              {'project':project,
                               'client':client,
                               'clients':clients,
                               'bugs':bugs})

def add_bug(request, client_name, project_name):

    project = get_project_from_name(project_name)
    title = request.POST['title']
    description = request.POST['description']
    priority = request.POST['priority']
    message = ''
    state = BugState(owner=users.get_current_user(),
                     message=message,
                     priority=priority)
    state.put()

    bug = Bug(title=title,
              description=description,
              project=project,
              state=state)
    bug.put()
    return HttpResponseRedirect(reverse('db.views.view_project', kwargs={'client_name':client_name,'project_name':project_name}))


def view_bug(request, project_name, bug_id):
    project = Project.gql("WHERE name = :name", name=project_name).get()
    bug = Bug.gql("WHERE project = :project AND id = :bug_id ", project=project, bug_id=bug_id).get()
    return render_to_response('bugs/view.html',
                              { 'project':project,
                                'bug':bug }
                              )
    

def add_project(request):
    name = request.POST['project_name']
    client_name = request.POST['client_name']
    client = Client.gql("WHERE name = :name", name=client_name).get()
    project = Project(name=name,
                      creator=users.get_current_user(),
                      client=client)        
    project.put()
    return HttpResponseRedirect('/')

def edit_project(request, client_name, project_name):
    project = get_project_from_name(project_name)
    project.description = request.POST['description']   
    project.put()
    return view_project(request, client_name, project_name)


def view_client(request, client_name):
    client = get_client_from_name(client_name)
    projects = Project.gql("WHERE client = :client", client=client)

    return render_to_response('clients/view.html', {'client':client,
                                                    'projects':projects})

def add_client(request):
    name = request.POST['client_name']       
    client = Client(name=name,
                      creator=users.get_current_user())        
    client.put()
    return HttpResponseRedirect('/')

def edit_client(request, id):
    client = db.get(db.Key(id))        
    client.description = request.POST['description']   
    client.put()
    return view_client(request, id)

