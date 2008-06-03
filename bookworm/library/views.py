from google.appengine.ext import db
from google.appengine.api import users

import os.path, re, sys, logging, urllib

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.conf import settings

from models import EpubDocument, EpubChapter, EpubArchive
from forms import EpubValidateForm


def index(request):
    documents = EpubArchive.all()
    user = users.get_current_user()
    if not user:
      greeting = ("<a href=\"%s\">Sign in or register</a>." %
                  users.create_login_url("/"))
      return render_to_response('login.html',  {'greeting': greeting})

    return render_to_response('index.html', {'documents':documents})

def upload(request):
    document = None
    if request.method == 'POST':
        form = EpubValidateForm(request.POST, request.FILES)
        if form.is_valid():

            data = form.cleaned_data['epub'].content
            document_name = form.cleaned_data['epub'].filename
            logging.info("Document name: %s" % document_name)
            document = EpubArchive(name=document_name)
            document.content = data
            document.explode()
            document.put()
            return HttpResponseRedirect('/')

    else:
        form = EpubValidateForm()        

    return render_to_response('upload.html', {'form':form, 'document':document})
