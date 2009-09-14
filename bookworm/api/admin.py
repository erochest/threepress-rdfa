from django.contrib import admin

from bookworm.api import models

class APIKeyAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.APIKey, APIKeyAdmin)
