from django import forms 

class EpubValidateForm(forms.Form):
    epub = forms.FileField()
 

