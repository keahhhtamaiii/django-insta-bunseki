from django import forms
from .forms import HashtagForm

class HashTagForm(forms.Form):
    hashtag = forms.CharField(max_length=100, label='ハッシュタグ')