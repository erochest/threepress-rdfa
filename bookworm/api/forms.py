from django import forms

class APIUploadForm(forms.Form):
    epub_data = forms.FileField()
    api_key = forms.CharField(max_length=255)
