import unittest
import os
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (LoginRequired, MediaNotFound)


class PrivateAccountException(Exception):
    "You are trying to interract with a private user"


class InvalidUsername(Exception):
    "Invalid link or username"


class InstagramTools:
    def __init__(self, username, password):
        self.client = Client()

        if os.path.exists('credential.json'):
            self.client.load_settings('credential.json')
            self.client.login(username, password)
        else:
            self.client.login(username, password)
            self.client.dump_settings('credential.json')

        try:
            self.client.account_info()
        except LoginRequired:
            self.client.relogin()
            self.client.dump_settings('credential.json')

    @staticmethod
    def extract_username(username):
        username = username.split('/')
        while '' in username:
            username.remove('')

        if len(username) == 0:
            raise InvalidUsername

        return username.pop()

    def get_user_id(self, username):
        return self.client.user_id_from_username(self.extract_username(
            username))

    def get_medias(self, user_id):
        if not self.is_public_account(user_id):
            raise PrivateAccountException
        return self.client.user_medias(user_id)

    def is_public_account(self, user_id):
        user = self.client.user_info(user_id)
        return not user.is_private

    def download_media(self, media, path='./') -> list:
        if media.media_type == 1:
            # Photo
            return [self.client.photo_download(media.pk, path)]
        elif media.media_type == 2 and media.product_type == 'feed':
            # Video
            return [self.client.video_download(media.pk, path)]
        elif media.media_type == 2 and media.product_type == 'igtv':
            # IGTV
            return [self.client.video_download(media.pk, path)]
        elif media.media_type == 2 and media.product_type == 'clips':
            # Reels
            return [self.client.video_download(media.pk, path)]
        elif media.media_type == 8:
            # Album
            return self.client.album_download(media.pk, path)

    def download_media_from_url(self, url) -> list:
        media_pk = self.client.media_pk_from_url(url)
        media = self.client.media_info(media_pk)
        return self.download_media(media)

    def download_story_from_url(self, url) -> Path:
        return self.client.story_download(self.client.story_pk_from_url(url))


class TestInstagramTools(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestInstagramTools, self).__init__(*args, **kwargs)
        self.ig_tools = InstagramTools('username', 'password')

    def test_extract_username(self):
        self.assertRaises(
            InvalidUsername, InstagramTools.extract_username, '//')
        self.assertEqual(InstagramTools.extract_username(
            'instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            '/instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'instagram_username/'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            '/instagram_username/'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'https://www.instagram.com/instagram_username'),
            'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'https://www.instagram.com/instagram_username/'),
            'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'http://www.instagram.com/instagram_username'),
            'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'http://www.instagram.com/instagram_username/'),
            'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'www.instagram.com/instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'www.instagram.com/instagram_username/'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'instagram.com/instagram_username'), 'instagram_username')
        self.assertEqual(InstagramTools.extract_username(
            'instagram.com/instagram_username'), 'instagram_username')


if __name__ == '__main__':
    unittest.main()
