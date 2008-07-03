from django import newforms as forms

class EpubValidateForm(forms.Form):
    epub = forms.FileField()

