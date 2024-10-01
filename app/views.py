from django.shortcuts import render, redirect
from django.views.generic.base import View
from datetime import datetime, date
from django.utils.timezone import localtime
from django.conf import settings
from .models import Insight, Post
from django.http.response import HttpResponse
import requests
import json
import math


class CallbackView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

class HashTagView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'app/hashtag.html', {})

def get_credentials():
    credentials = {}
    credentials['access_token'] = settings.ACCESS_TOKEN
    credentials['instagram_account_id'] = settings.INSTAGRAM_ACCOUNT_ID
    credentials['graph_domain'] = 'https://graph.facebook.com/'
    credentials['graph_version'] = 'v8.0'
    credentials['endpoint_base'] = credentials['graph_domain'] + credentials['graph_version'] + '/'
    credentials['ig_username'] = 'ruru___cafe'
    return credentials

def call_api(url, endpoint_params=''):
    try:
        response = requests.get(url, params=endpoint_params)
        response.raise_for_status()
        return {'json_data': response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        return {'json_data': {}}

def get_account_info(params):
    endpoint_params = {
        'fields': 'business_discovery.username(' + params['ig_username'] + '){'
        'username,profile_picture_url,follows_count,followers_count,media_count,'
        'media.limit(10){comments_count,like_count,caption,media_url,permalink,timestamp,media_type,'
        'children{media_url,media_type}}}',
        'access_token': params['access_token']
    }
    url = params['endpoint_base'] + params['instagram_account_id']
    return call_api(url, endpoint_params)

def get_media_insights(params):
    endpoint_params = {
        'metric': 'engagement,impressions,reach,saved',
        'access_token': params['access_token']
    }
    url = params['endpoint_base'] + params['media_id'] + '/insights'
    return call_api(url, endpoint_params)

class IndexView(View):
    def get(self, request, *args, **kwargs):
        params = get_credentials()
        account_response = get_account_info(params)
        business_discovery = account_response['json_data'].get('business_discovery', {})

        # 最初の投稿日を設定
        first_post_date = datetime(2023, 12, 16).date()


        account_data = {
            'profile_picture_url': business_discovery.get('profile_picture_url', ''),
            'username': business_discovery.get('username', ''),
            'followers_count': business_discovery.get('followers_count', 0),
            'follows_count': business_discovery.get('follows_count', 0),
            'media_count': business_discovery.get('media_count', 0),
        }
        today = date.today()

        # 最初の投稿日から今日までのデータを更新
        if today >= first_post_date:
            obj, created = Insight.objects.update_or_create(
                label=today,
                defaults={
                    'follower': business_discovery.get('followers_count', 0),
                    'follows': business_discovery.get('follows_count', 0),
                }
            )

        media_insight_data = Insight.objects.filter(label__gte=first_post_date).order_by("label")
        follower_data = [data.follower for data in media_insight_data]
        follows_data = [data.follows for data in media_insight_data]
        ff_data = [math.floor((data.follower / data.follows) * 100) / 100 for data in media_insight_data]
        label_data = [data.label for data in media_insight_data]

        like = 0
        comments = 0
        count = 1
        post_timestamp = ''
        for data in business_discovery.get('media', {}).get('data', []):
            timestamp = localtime(datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime('%Y-%m-%d')
            if post_timestamp == timestamp:
                like += data['like_count']
                comments += data['comments_count']
                count += 1
            else:
                like = data['like_count']
                comments = data['comments_count']
                post_timestamp = timestamp
                count = 1

            if datetime.strptime(post_timestamp, '%Y-%m-%d').date() >= first_post_date:
                obj, created = Post.objects.update_or_create(
                    label=timestamp,
                    defaults={
                        'like': like,
                        'comments': comments,
                        'count': count,
                    }
                )

        post_data = Post.objects.filter(label__gte=first_post_date).order_by("label")
        like_data = [data.like for data in post_data]
        comments_data = [data.comments for data in post_data]
        count_data = [data.count for data in post_data]
        post_label_data = [data.label for data in post_data]

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

        latest_media_data = business_discovery.get('media', {}).get('data', [])[0] if business_discovery.get('media') else {}
        print("Latest Media Data:", latest_media_data)

        params['media_id'] = latest_media_data.get('id', '')

        media_response = get_media_insights(params)
        media_data = media_response.get('json_data', {}).get('data', None)

        if latest_media_data.get('media_type') == 'CAROUSEL_ALBUM':
            if 'children' in latest_media_data:
                media_url = latest_media_data['children']['data'][0]['media_url']
                media_type = 'VIDEO' if latest_media_data['children']['data'][0]['media_type'] == 'VIDEO' else 'IMAGE'
            else:
                media_url = 'http://placehold.jp/500x500.png?text=No+Media'
                media_type = 'UNKNOWN'
        else:
            media_url = latest_media_data.get('media_url', 'http://placehold.jp/500x500.png?text=No+Media')
            media_type = latest_media_data.get('media_type', 'UNKNOWN')

        insight_media_data = {
            'caption': latest_media_data.get('caption', 'No caption available'),
            'media_type': media_type,
            'media_url': media_url,
            'permalink': latest_media_data.get('permalink', ''),
            'timestamp': localtime(datetime.strptime(latest_media_data.get('timestamp', ''), '%Y-%m-%dT%H:%M:%S%z')).strftime('%Y/%m/%d %H:%M') if latest_media_data.get('timestamp') else 'Unknown',
            'like_count': latest_media_data.get('like_count', 0),
            'comments_count': latest_media_data.get('comments_count', 0),
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