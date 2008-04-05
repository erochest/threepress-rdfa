from django.contrib.sitemaps import Sitemap
from models import Document

class ThreepressSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Document.objects.all()

    def lastmod(self, obj):
        return obj.add_date
