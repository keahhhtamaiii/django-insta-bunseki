from django.db import models


class Insight(models.Model):
    follower = models.IntegerField('フォロワー')
    follows = models.IntegerField('フォロー')
    label = models.CharField('作成日', max_length=100)

    def __str__(self):
        return str(self.label)


class Post(models.Model):
    like = models.IntegerField('いいね')
    comments = models.IntegerField('コメント数')
    count = models.IntegerField('投稿数')
    label = models.CharField('投稿日', max_length=100)

    def __str__(self):
        return str(self.label)


class HashTag(models.Model):
    tag = models.CharField('ハッシュタグ', max_length=100)
    count = models.IntegerField('投稿数')
    label = models.CharField('投稿日', max_length=100)

    def __str__(self):
        return str(self.label) + ':' + str(self.tag)

