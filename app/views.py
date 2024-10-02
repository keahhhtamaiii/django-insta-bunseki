from django.views.generic import View
from django.shortcuts import render, redirect
from datetime import datetime, date
from django.utils.timezone import localtime
from django.conf import settings
from .models import Insight, Post, HashTag
from .forms import HashtagForm
import requests
import json
import math
import pandas as pd


# Instagram Graph API認証情報
def get_credentials():
    credentials = {}
    credentials['access_token'] = settings.ACCESS_TOKEN
    credentials['instagram_account_id'] = settings.INSTAGRAM_ACCOUNT_ID
    credentials['graph_domain'] = 'https://graph.facebook.com/'
    credentials['graph_version'] = 'v8.0'
    credentials['endpoint_base'] = credentials['graph_domain'] + credentials['graph_version'] + '/'
    credentials['ig_username'] = 'ruru___cafe'
    return credentials


# Instagram Graph APIコール
def call_api(url, endpoint_params=''):
    # API送信
    if endpoint_params:
        data = requests.get(url, endpoint_params)
    else:
        data = requests.get(url)

    response = {}
    # API送信結果をjson形式で保存
    response['json_data'] = json.loads(data.content)
    return response

# ユーザーアカウント情報取得
def get_account_info(params):
    # エンドポイント
    # https://graph.facebook.com/{graph-api-version}/{ig-user-id}?fields={fields}&access_token={access-token}

    endpoint_params = {}
    # ユーザ名、プロフィール画像、フォロワー数、フォロー数、投稿数、メディア情報取得
    endpoint_params['fields'] = 'business_discovery.username(' + params['ig_username'] + '){\
        username,profile_picture_url,follows_count,followers_count,media_count,\
        media.limit(10){comments_count,like_count,caption,media_url,permalink,timestamp,media_type,\
        children{media_url,media_type}}}'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id']
    return call_api(url, endpoint_params)


# 特定メディアIDのインサイト取得
def get_media_insights(params):
    # エンドポイント
    # https://graph.facebook.com/{graph-api-version}/{ig-media-id}/insights?metric={metric}&access_token={access-token}

    endpoint_params = {}
    # エンゲージメント、インプレッション、リーチ、保存情報取得
    endpoint_params['metric'] = 'engagement,impressions,reach,saved'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['media_id'] + '/insights'
    return call_api(url, endpoint_params)


# ハッシュタグ検索
def get_hashtag_id(params):
    # エンドポイント
    # https://graph.facebook.com/{graph-api-version}/ig_hashtag_search?user_id={user-id}&q={hashtag-name}&fields={fields}&access_token={access-token}

    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    # 指定ハッシュタグ
    endpoint_params['q'] = params['hashtag_name']
    endpoint_params['fields'] = 'id,name'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + 'ig_hashtag_search'
    return call_api(url, endpoint_params)


def get_hashtag_media(params):
    # エンドポイント
    # https://graph.facebook.com/{graph-api-version}/{ig-hashtag-id}/recent_media?user_id={user-id}&fields={fields}

    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    endpoint_params['fields'] = 'id,media_type,media_url,children{media_url,media_type},permalink,caption,like_count,comments_count,timestamp'
    endpoint_params['limit'] = 50
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['hashtag_id'] + '/recent_media'
    return call_api(url, endpoint_params)


class IndexView(View):
    def get(self, request, *args, **kwargs):
        # Instagram Graph API認証情報取得
        params = get_credentials()
        # アカウント情報取得
        account_response = get_account_info(params)
        business_discovery = account_response['json_data']['business_discovery']
        # print(business_discovery)
        account_data = {
            'profile_picture_url': business_discovery['profile_picture_url'],
            'username': business_discovery['username'],
            'followers_count': business_discovery['followers_count'],
            'follows_count': business_discovery['follows_count'],
            'media_count': business_discovery['media_count'],
        }
        # 本日の日付
        today = date.today()

        # Insightデーターベースに保存
        obj, created = Insight.objects.update_or_create(
            label=today,
            defaults={
                'follower': business_discovery['followers_count'],
                'follows': business_discovery['follows_count'],
            }
        )

        # Insightデーターベースからデータを取得
        # order_byで昇順に並び替え
        media_insight_data = Insight.objects.all().order_by("label")
        follower_data = []
        follows_data = []
        ff_data = []
        label_data = []
        for data in media_insight_data:
            # フォロワー数
            follower_data.append(data.follower)
            # フォロー数
            follows_data.append(data.follows)
            # フォロー数、フォロワー数比率(小数点2桁)
            ff = math.floor((data.follower / data.follows) * 100) / 100
            ff_data.append(ff)
            # ラベル
            label_data.append(data.label)

        # アカウント情報から投稿情報を取得
        like = 0
        comments = 0
        count = 1
        post_timestamp = ''
        for data in business_discovery['media']['data']:
            # 投稿日取得
            timestamp = localtime(datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime('%Y-%m-%d')
            # 同じ日に複数の投稿がある場合、各データを足していく
            if post_timestamp == timestamp:
                like += data['like_count']
                comments += data['comments_count']
                count += 1
            else:
                like = data['like_count']
                comments = data['comments_count']
                post_timestamp = timestamp
                count = 1

            # 投稿データベースに保存
            obj, created = Post.objects.update_or_create(
                label=timestamp,
                defaults={
                    'like': like,
                    'comments': comments,
                    'count': count,
                }
            )

        # Postデーターベースからデータを取得
        # order_byで昇順に並び替え
        post_data = Post.objects.all().order_by("label")
        like_data = []
        comments_data = []
        count_data = []
        post_label_data = []
        for data in post_data:
            # いいね数
            like_data.append(data.like)
            # コメント数
            comments_data.append(data.comments)
            # 投稿数
            count_data.append(data.count)
            # ラベル
            post_label_data.append(data.label)

        # アカウントのインサイトデータ
        insight_data = {
            'follower_data': follower_data,
            'follows_data': follows_data,
            'ff_data': ff_data,
            'label_data': label_data,
            'like_data': like_data,
            'comments_data': comments_data,
            'count_data': count_data,
            'post_label_data': post_label_data,
        }

        # 最新の投稿情報を取得
        latest_media_data = business_discovery['media']['data'][0]
        params['media_id'] = latest_media_data['id']
        media_response = get_media_insights(params)
        media_data = media_response.get('json_data', {}).get('data', None)
        if latest_media_data['media_type'] == 'CAROUSEL_ALBUM':
            media_url = latest_media_data['children']['data'][0]['media_url']
            if latest_media_data['children']['data'][0]['media_type'] == 'VIDEO':
                media_type = 'VIDEO'
            else:
                media_type = 'IMAGE'
        else:
            media_url = latest_media_data['media_url']
            media_type = latest_media_data['media_type']

        # メディアのインサイトデータ
        insight_media_data = {
            'caption': latest_media_data['caption'],
            'media_type': media_type,
            'media_url': media_url,
            'permalink': latest_media_data['permalink'],
            'timestamp': localtime(datetime.strptime(latest_media_data['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime('%Y/%m/%d %H:%M'),
            'like_count': latest_media_data['like_count'],
            'comments_count': latest_media_data['comments_count'],
            'engagement': media_data[0]['values'][0]['value'] if media_data else None,
            'impression': media_data[1]['values'][0]['value'] if media_data else None,
            'reach': media_data[2]['values'][0]['value'] if media_data else None,
            'save': media_data[3]['values'][0]['value'] if media_data else None,
        }

        return render(request, 'app/index.html', {
            'today': today.strftime('%Y-%m-%d'),
            'account_data': account_data,
            'insight_data': json.dumps(insight_data),
            'insight_media_data': insight_media_data,
        })

class HashtagView(View):
    # メディアのリストを作成
    def get_media_list(self, hashtag_media_response, hashtag_media_list):
        for item in hashtag_media_response['json_data']['data']:
            # カルーセルの場合は一番最初のメディアを取得
            if item['media_type'] == 'CAROUSEL_ALBUM':
                media_url = item['children']['data'][0]['media_url']
                if item['children']['data'][0]['media_type'] == 'VIDEO':
                    media_type = 'VIDEO'
                else:
                    media_type = 'IMAGE'
            else:
                try:
                    media_url = item['media_url']
                except KeyError:
                    media_url = 'http://placehold.jp/500x500.png?text=None'
                media_type = item['media_type']

            # 投稿日
            timestamp = localtime(datetime.strptime(item['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime('%Y-%m-%d')

            hashtag_media_list.append([
                media_type,
                media_url,
                item['permalink'],
                item['like_count'],
                item['comments_count'],
                timestamp,
            ])
        return hashtag_media_list

    def get(self, request, *args, **kwargs):
        # 検索フォーム
        form = HashtagForm(request.POST or None)

        return render(request, 'app/search.html', {
            'form': form
        })

    def post(self, request, *args, **kwargs):
        form = HashtagForm(request.POST or None)

        # フォームのバリデーション
        if form.is_valid():
            # フォームからデータを取得
            hashtag = form.cleaned_data['hashtag']

            # Instagram Graph API認証情報取得
            params = get_credentials()

            # ハッシュタグ設定
            params['hashtag_name'] = hashtag

            # ハッシュタグID取得
            hashtag_id_response = get_hashtag_id(params)

            # ハッシュタグID設定
            params['hashtag_id'] = hashtag_id_response['json_data']['data'][0]['id'];

            # ハッシュタグ検索
            hashtag_media_response = get_hashtag_media(params)

            hashtag_media_list = []

            # メディアのリストを作成
            hashtag_media_list = self.get_media_list(hashtag_media_response, hashtag_media_list)

            # 次のデータが存在するまで繰り返す
            while True:
                # 次のデータが存在しない場合はbreak
                if not hashtag_media_response['json_data'].get('paging'):
                    break
                next_url = hashtag_media_response['json_data']['paging']['next']
                hashtag_data = hashtag_media_response['json_data']['data']
                if hashtag_data and next_url:
                    # 次のデータを取得
                    hashtag_media_response = call_api(next_url)
                    # メディアのリストを作成
                    hashtag_media_list = self.get_media_list(hashtag_media_response, hashtag_media_list)
                else:
                    # 次のデータが存在しない場合はbreak
                    break

            # データフレームの作成
            hashtag_media_data = pd.DataFrame(hashtag_media_list, columns=[
                'media_type',
                'media_url',
                'permalink',
                'like_count',
                'comments_count',
                'timestamp',
            ])

            # いいね数、コメント数順で並び替え
            hashtag_media_data = hashtag_media_data.sort_values(['like_count', 'comments_count'], ascending=[False, False])

            post_counts = hashtag_media_data['timestamp'].value_counts().to_dict()

            for key, value in post_counts.items():
                # ハッシュタグデータベースに保存
                obj, created = HashTag.objects.update_or_create(
                    label=key,
                    tag=hashtag,
                    defaults={
                        'count': value,
                    }
                )

            # Postデーターベースからデータを取得
            # order_byで昇順に並び替え
            hashtag_data = HashTag.objects.filter(tag=hashtag).order_by("label")
            count_data = []
            label_data = []
            for data in hashtag_data:
                # 投稿数
                count_data.append(data.count)
                # ラベル
                label_data.append(data.label)

            # ハッシュタグ毎の投稿データ
            hashtag_count_data = {
                'count_data': count_data,
                'label_data': label_data,
            }

            return render(request, 'app/hashtag.html', {
                'hashtag_media_data': hashtag_media_data,
                'hashtag': hashtag,
                'hashtag_count_data': json.dumps(hashtag_count_data),
            })
        else:
            redirect('hashtag')
