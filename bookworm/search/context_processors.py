import logging
from django.conf import settings

from bookworm.search.forms import EpubSearchForm
from bookworm.library.models import EpubArchive


log = logging.getLogger('context_processors')

def count_books(user):
    return EpubArchive.objects.filter(user_archive__user=user).distinct().count()
 
def search(request):
    form = None
    if not request.user.is_anonymous():
        form = EpubSearchForm()
    return {'search_form': form }

def _get_name_for_language(lang):
    for l in settings.LANGUAGES:
        if lang == l[0]:
            return l[1]
    return lang
