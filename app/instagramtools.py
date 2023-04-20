import unittest
import os
import logging
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (LoginRequired, MediaNotFound,
                                   HighlightNotFound, UserNotFound)


class PrivateAccountException(Exception):
    "You are trying to interact with a private user."


def retry_decorator(relogin_attempts=3):
    def decorator(func):
        def wrapped_func(*args, **kwargs):
            for i in range(relogin_attempts):
                try:
                    result = func(*args, **kwargs)
                except LoginRequired as err:
                    exception = err
                    args[0].relogin()
                except Exception as err:
                    exception = err
                else:
                    return result
            raise exception

        return wrapped_func

    return decorator


class InstagramTools:
    def __init__(self, username, password):
        self.logger = logging.getLogger('instasub')
        self.client = Client()
        self.set_delay(False)
        self._login(username, password)

    def _login(self, username, password):
        self.logger.info('Sing in to instagram: username - {0} password - {1}'.format(username, password))
        self.credential_file = '/ext/credential.json'
        if os.path.exists(self.credential_file):
            self.client.load_settings(self.credential_file)
            res = self.client.login(username, password)
        else:
            res = self.client.login(username, password)
            self.client.dump_settings(self.credential_file)

    def relogin(self):
        self.logger.warning('Relogin to instagram')
        try:
            self.client.relogin()
        except Exception as e:
            print(str(e))
        self.client.dump_settings(self.credential_file)

    def set_delay(self, delay):
        if delay:
            self.client.request_timeout = 1
        else:
            self.client.request_timeout = 0

    @staticmethod
    def extract_username(username):
        username = username.split('/')
        while '' in username:
            username.remove('')

        if len(username) == 0:
            raise UserNotFound

        return username.pop()

    @retry_decorator()
    def get_user_id(self, username) -> str:
        self.logger.debug('Get user id: {0}'.format(username))
        return self.client.user_id_from_username(self.extract_username(username))

    @retry_decorator()
    def get_user_medias(self, user_id):
        self.logger.debug('Get user media: {0}'.format(user_id))
        if not self.is_public_account(user_id):
            raise PrivateAccountException
        return self.client.user_medias(user_id)

    @retry_decorator()
    def get_user_tagged_medias(self, user_id):
        self.logger.debug('Get user tagged media: {0}'.format(user_id))
        if not self.is_public_account(user_id):
            raise PrivateAccountException
        return self.client.usertag_medias(user_id)

    @retry_decorator()
    def is_public_account(self, user_id):
        self.logger.debug('Check account privacy: {0}'.format(user_id))
        user = self.client.user_info(user_id)
        return not user.is_private

    @retry_decorator()
    def download_media(self, media, path) -> list:
        self.logger.debug('Download media: {0}'.format(media))
        if not os.path.exists(path):
            os.makedirs(path)
        if media.media_type == 1:
            return [self.client.photo_download(media.pk, path)]
        elif media.media_type == 2:
            return [self.client.video_download(media.pk, path)]
        elif media.media_type == 8:
            return self.client.album_download(media.pk, path)

    @retry_decorator()
    def download_media_from_url(self, url, path) -> list:
        self.logger.debug('Download media: {0}'.format(url))
        media_pk = self.client.media_pk_from_url(url)
        media = self.client.media_info(media_pk)
        return self.download_media(media, path)

    @retry_decorator()
    def get_media_info_from_url(self, url) -> str:
        self.logger.debug('Get media info: {0}'.format(url))
        media_pk = self.client.media_pk_from_url(url)
        media = self.client.media_info(media_pk)
        return self.get_media_info(media)

    @retry_decorator()
    def get_media_info(self, media) -> str:
        self.logger.debug('Get media info: {0}'.format(media))
        info = 'User: ' + media.user.username
        if media.user.full_name:
            info = info + ' - ' + media.user.full_name
        info = info + '\n'
        if media.caption_text != '':
            info = info + 'Caption: ' + media.caption_text + '\n'
        info = info + 'Created at: ' + media.taken_at.strftime("%d.%m.%y %H:%M:%S") + '\n'
        if media.location:
            info = info + 'Location: ' + media.location.name + '\n'
        info = info + 'Like count: ' + str(media.like_count) + '\n'
        return info

    @retry_decorator()
    def get_user_info(self, user_id) -> str:
        self.logger.debug('Get user info: {0}'.format(user_id))
        user_info = self.client.user_info(user_id)
        info = 'Id: ' + user_info.pk
        info = info + '\nUsername: ' + user_info.username
        if user_info.full_name:
            info = info + '\nFull name: ' + user_info.full_name
        if user_info.biography:
            info = info + '\nBiography: ' + user_info.biography
        if user_info.address_street:
            info = info + '\nAddress street: ' + user_info.address_street
        if user_info.city_name:
            info = info + '\nCity name: ' + user_info.city_name
        if user_info.contact_phone_number:
            info = info + '\nContact phone number: ' + user_info.contact_phone_number
        if user_info.public_phone_number:
            info = info + '\nPublic phone number: ' + user_info.public_phone_number
        if user_info.public_email:
            info = info + '\nPublic email: ' + user_info.public_email
        info = info + '\nMedia count: ' + str(user_info.media_count)
        info = info + '\nFollower count: ' + str(user_info.follower_count)
        info = info + '\nFollowing count: ' + str(user_info.following_count)
        return info

    @retry_decorator()
    def get_user_pic(self, user_id, path) -> str:
        self.logger.debug('Get user pic: {0}'.format(user_id))
        user_info = self.client.user_info(user_id)
        return self.client.photo_download_by_url(user_info.profile_pic_url_hd, user_id, path)

    @retry_decorator()
    def get_media_comments(self, media) -> str:
        self.logger.debug('Get media comments: {0}'.format(media))
        comments = self.client.media_comments(media.pk, 0)
        if len(comments) == 0:
            return ''
        formatted_result = '\nComments:\n'
        for comment in comments:
            if comment.text == '':
                continue
            formatted_result = formatted_result + comment.created_at_utc.strftime("%d.%m.%y/%H:%M:%S") + '/'
            formatted_result = formatted_result + comment.user.username
            if comment.user.full_name:
                formatted_result = formatted_result + '/' + comment.user.full_name
            formatted_result = formatted_result + ': ' + comment.text + '\n'
        return formatted_result

    @retry_decorator()
    def download_story_from_url(self, url, path) -> Path:
        self.logger.debug('Download story: {0}'.format(url))
        if not os.path.exists(path):
            os.makedirs(path)
        story_pk = self.client.story_pk_from_url(url)
        return self.client.story_download(story_pk, story_pk, path)

    @retry_decorator()
    def get_highlights(self, user_id) -> list:
        self.logger.debug('Get user highlights: {0}'.format(user_id))
        return self.client.user_highlights(user_id)

    @retry_decorator()
    def get_highlight_info(self, highlight) -> str:
        self.logger.debug('Get highlight info: {0}'.format(highlight))
        info = 'User: ' + highlight.user.username
        if highlight.user.full_name:
            info = info + ' - ' + highlight.user.full_name
        info = info + '\nTitle: ' + highlight.title
        info = info + '\nCreated at: ' + highlight.created_at.strftime("%d.%m.%y %H:%M:%S")
        return info

    @retry_decorator()
    def download_highlight(self, highlight, path) -> list:
        self.logger.debug('Download highlight: {0}'.format(highlight))
        if not os.path.exists(path):
            os.makedirs(path)
        paths = []
        info = self.client.highlight_info(highlight.pk)  # doesn't work with highlight.items
        for item in info.items:
            if item.media_type == 1:
                paths.append(self.client.photo_download_by_url(item.thumbnail_url, folder=path))
            elif item.media_type == 2:
                paths.append(self.client.video_download_by_url(item.video_url, folder=path))
        return paths

    @retry_decorator()
    def download_highlights_from_url(self, url, path):
        self.logger.debug('Download highlight: {0}'.format(url))
        return self.download_highlight(self.client.highlight_info(self.client.highlight_pk_from_url(url)), path)


class TestInstagramTools(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestInstagramTools, self).__init__(*args, **kwargs)
        self.ig_tools = InstagramTools('username', 'password')

    def test_extract_username(self):
        self.assertRaises(UserNotFound, InstagramTools.extract_username, '//')
        self.assertEqual(InstagramTools.extract_username('instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username('/instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username('instagram_username/'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username('/instagram_username/'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username('https://www.instagram.com/instagram_username'),
                         'instagram_username')
        self.assertEqual(InstagramTools.extract_username('https://www.instagram.com/instagram_username/'),
                         'instagram_username')
        self.assertEqual(InstagramTools.extract_username('http://www.instagram.com/instagram_username'),
                         'instagram_username')
        self.assertEqual(InstagramTools.extract_username('http://www.instagram.com/instagram_username/'),
                         'instagram_username')
        self.assertEqual(InstagramTools.extract_username('www.instagram.com/instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username('www.instagram.com/instagram_username/'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username('instagram.com/instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username('instagram.com/instagram_username'), 'instagram_username')


if __name__ == '__main__':
    unittest.main()
