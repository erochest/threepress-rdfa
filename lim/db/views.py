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
    p = Project.gql("WHERE name = :name", name=unsafe_name(name)).get()
    if not p:
        raise Http404
    return p

def get_client_from_name(name):
    c = Client.gql("WHERE name = :name", name=unsafe_name(name)).get()
    if not c:
        raise Http404
    return c

def get_clients():
    return Client.all()
    
def index(request):
    projects = Project.all()
    user = users.get_current_user()
    if not user:
      greeting = ("<a href=\"%s\">Sign in or register</a>." %
                  users.create_login_url("/"))
      return render_to_response('login.html',  {'greeting': greeting})

    return render_to_response('index.html', {'projects':projects,
                                             'clients':get_clients()})


def view_project(request, client_name, project_name):
    project = get_project_from_name(project_name)
    if not project:
        raise Http404
    client = get_client_from_name(client_name)
    if not client:
        raise Http404

    # Get all bugs
    bugs = Bug.gql("WHERE project = :project ORDER BY created DESC", project=project)
    return render_to_response('projects/view.html', 
                              {'project':project,
                               'client':client,
                               'clients':get_clients(),
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
    bug.bug_num = bug.key().id()
    bug.put()
    return HttpResponseRedirect(reverse('db.views.view_project', kwargs={'client_name':client_name,'project_name':project_name}))


def view_bug(request, client_name, project_name, bug_num):
    project = get_project_from_name(project_name)
    client = get_client_from_name(client_name)
    bug = Bug.gql("WHERE project = :project AND bug_num = :bug_num ", project=project, bug_num=int(bug_num)).get()
    if not bug:
        raise Http404
    return render_to_response('bugs/view.html',
                              { 'project':project,
                                'client':client,
                                'clients':get_clients(),
                                'bug':bug }
                              )
    

def add_project(request):
    name = request.POST['project_name']
    client_name = request.POST['client_name']
    description = request.POST['project_description']
    client = Client.gql("WHERE name = :name", name=client_name).get()
    project = Project(name=name,
                      creator=users.get_current_user(),
                      description=description,
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
    if not client:
        raise Http404
    return render_to_response('clients/view.html', {'client':client,
                                                    'clients':get_clients(),
                                                    'projects':projects})

def add_client(request):
    name = request.POST['client_name']       
    description = request.POST['client_description']   
    client = Client(name=name,
                    description=description,
                    creator=users.get_current_user())        
    client.put()
    return HttpResponseRedirect('/')

def edit_client(request, client_name):
    client = get_client_from_name(client_name)
    client.description = request.POST['client_description']   
    client.put()
    return view_client(request, id)

