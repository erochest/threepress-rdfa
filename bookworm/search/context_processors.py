import logging
from django.conf import settings

from forms import EpubSearchForm
from library.models import EpubArchive


log = logging.getLogger('context_processors')

def count_books(user):
    return EpubArchive.objects.filter(user_archive__user=user).distinct().count()
 
def search(request):
    form = None
    current_search_language = 'English'
    if (not request.user.is_anonymous()) and count_books(request.user) > 0:

        # Did we just update the setting?
        if 'language' in request.GET:
            language_value = request.GET['language']

        # Otherwise get language from the session
        elif settings.LANGUAGE_COOKIE_NAME in request.session:
            language_value = request.session[settings.LANGUAGE_COOKIE_NAME]

        # or from the user's profile
        elif request.user.get_profile().language is not None:
            language_value = request.user.get_profile().language

        if language_value:
            current_search_language = _get_name_for_language(language_value)
            
        if 'q' in request.GET:
            form = EpubSearchForm(request.GET, lang=language_value)
        else:
            form = EpubSearchForm(lang=language_value)

    return {'search_form': form,
            'current_search_language': current_search_language}
    

def _get_name_for_language(lang):
    for l in settings.LANGUAGES:
        if lang == l[0]:
            return l[1]
    return lang
