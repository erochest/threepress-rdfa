import logging

from django import forms
from django.conf import settings

from xapian import Stem

log = logging.getLogger('search.forms')

langs = Stem.get_available_languages()
choices = []
for l in langs.split(' '):
    choices.append( (l, l.capitalize() ) )

class EpubSearchForm(forms.Form):
    q = forms.CharField()
    language = forms.ChoiceField(choices=settings.LANGUAGES,
                                 initial='en',
                                 widget=forms.RadioSelect)
    def __init__(self, *args, **kwargs):
        lang = None
        if 'lang' in kwargs:
            lang = kwargs['lang'].lower()
            del kwargs['lang']
        super(EpubSearchForm, self).__init__(*args, **kwargs)        
        if lang:
            log.debug("Setting initial lang value to '%s'" % lang)
            self.fields['language'].initial = lang


