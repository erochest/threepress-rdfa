from django.contrib import admin
from models import EpubArchive, BookAuthor,HTMLFile,StylesheetFile, ImageFile, UserPref


class EpubArchiveAdmin(admin.ModelAdmin):
    fields=('title','name','owner','orderable_author','toc', 'opf')
    list_filter=('orderable_author',)
    search_fields = ['title']
    ordering = ('title', '-created_time')
    list_per_page = 500

class BookAuthorAdmin(admin.ModelAdmin):
    ordering = ('name',)

class HTMLFileAdmin(admin.ModelAdmin):
    fields=('title','filename','processed_content','is_read')
    ordering = ('title',)

class StylesheetFileAdmin(admin.ModelAdmin):
    fields=('filename',)

class ImageFileAdmin(admin.ModelAdmin):    
    fields=('filename',)

class UserPrefAdmin(admin.ModelAdmin):
    pass

admin.site.register(EpubArchive, EpubArchiveAdmin)
admin.site.register(BookAuthor, BookAuthorAdmin)
admin.site.register(HTMLFile, HTMLFileAdmin)
admin.site.register(StylesheetFile, StylesheetFileAdmin)
admin.site.register(ImageFile, ImageFileAdmin)
admin.site.register(UserPref, UserPrefAdmin)


