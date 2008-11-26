from django.contrib import admin
from models import EpubArchive, BookAuthor,HTMLFile,StylesheetFile, ImageFile, UserPref, EpubPublisher, Subject


class EpubArchiveAdmin(admin.ModelAdmin):
    fields=('title','name','owner','orderable_author','toc', 'opf', 'publishers', 'subjects', 'language', 'identifier', 'rights', 'indexed')
    list_display=('title','created_time','identifier','orderable_author', 'publisher')
    list_filter=('orderable_author',)
    search_fields = ['title']
    ordering = ('-created_time', 'title')
    list_per_page = 500

class BookAuthorAdmin(admin.ModelAdmin):
    ordering = ('name',)

class HTMLFileAdmin(admin.ModelAdmin):
    fields=('title','filename','processed_content','is_read', 'idref')
    ordering = ('title','path')
    search_fields = ['title', 'filename']

class StylesheetFileAdmin(admin.ModelAdmin):
    fields=('filename','path')

class ImageFileAdmin(admin.ModelAdmin):    
    fields=('filename','path', 'content_type')

class EpubPublisherAdmin(admin.ModelAdmin):
    fields=('name',)
    ordering=('name',)

class SubjectAdmin(admin.ModelAdmin):
    ordering=('name',)

class UserPrefAdmin(admin.ModelAdmin):
    fields=('user', 'fullname', 'country', 'language', 'timezone','nickname','open_to_last_chapter')
    list_display=('username', 'fullname','language')
    search_fields = ['fullname', 'language', 'country']
    list_per_page = 500

admin.site.register(EpubArchive, EpubArchiveAdmin)
admin.site.register(BookAuthor, BookAuthorAdmin)
admin.site.register(HTMLFile, HTMLFileAdmin)
admin.site.register(StylesheetFile, StylesheetFileAdmin)
admin.site.register(ImageFile, ImageFileAdmin)
admin.site.register(UserPref, UserPrefAdmin)
admin.site.register(EpubPublisher, EpubPublisherAdmin)
admin.site.register(Subject, SubjectAdmin)

