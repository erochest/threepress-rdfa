import logging

from django import forms

log = logging.getLogger('search.forms')

class EpubSearchForm(forms.Form):
    q = forms.CharField()
