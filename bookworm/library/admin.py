from django.contrib import admin
from models import *

class EpubArchiveAdmin(admin.ModelAdmin):
    pass


class BookAuthorAdmin(admin.ModelAdmin):
    pass

class HTMLFileAdmin(admin.ModelAdmin):
    pass

class StylesheetFileAdmin(admin.ModelAdmin):
    pass

class ImageFileAdmin(admin.ModelAdmin):
    pass

class UserPrefAdmin(admin.ModelAdmin):
    pass

admin.site.register(EpubArchive, EpubArchiveAdmin)
admin.site.register(BookAuthor, BookAuthorAdmin)
admin.site.register(HTMLFile, HTMLFileAdmin)
admin.site.register(StylesheetFile, StylesheetFileAdmin)
admin.site.register(ImageFile, ImageFileAdmin)
admin.site.register(UserPref, UserPrefAdmin)


