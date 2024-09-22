from django import forms


class HashTagForm(forms.Form):
    hashtag = forms.CharField(max_length=100, label='ハッシュタグ')