from django import forms

class HashtagForm(forms.Form):
    hashtag = forms.CharField(max_length=100, label='ハッシュタグ')