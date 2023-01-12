import unittest
import os
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (LoginRequired, MediaNotFound,
                                   HighlightNotFound, UserNotFound)


class PrivateAccountException(Exception):
    "You are trying to interract with a private user"


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
            raise UserNotFound

        return username.pop()

    def get_user_id(self, username) -> str:
        return self.client.user_id_from_username(self.extract_username(
            username))

    def get_user_medias(self, user_id):
        if not self.is_public_account(user_id):
            raise PrivateAccountException
        return self.client.user_medias(user_id)

    def get_user_tagged_medias(self, user_id):
        if not self.is_public_account(user_id):
            raise PrivateAccountException
        return self.client.usertag_medias(user_id)

    def is_public_account(self, user_id):
        user = self.client.user_info(user_id)
        return not user.is_private

    def download_media(self, media, path=None) -> list:
        download_path = ''
        if path:
            download_path = path + str(media.pk)
            if not os.path.exists(download_path):
                os.makedirs(download_path)
        if media.media_type == 1:
            return [self.client.photo_download(media.pk, download_path)]
        elif media.media_type == 2:
            return [self.client.video_download(media.pk, download_path)]
        elif media.media_type == 8:
            return self.client.album_download(media.pk, download_path)

    def download_media_from_url(self, url) -> list:
        media_pk = self.client.media_pk_from_url(url)
        media = self.client.media_info(media_pk)
        return self.download_media(media)

    def download_story_from_url(self, url) -> Path:
        return self.client.story_download(self.client.story_pk_from_url(url))

    def get_highlights(self, user_id) -> list:
        return self.client.user_highlights(user_id)

    def download_highlight(self, highlight, path=None) -> list:
        download_path = ''
        if path:
            download_path = path + str(highlight)
            if not os.path.exists(download_path):
                os.makedirs(download_path)
        info = self.client.highlight_info(highlight)
        paths = []
        for item in info.items:
            if item.media_type == 1:
                paths.append(self.client.photo_download_by_url(
                    item.thumbnail_url, folder=download_path))
            elif item.media_type == 2:
                paths.append(self.client.video_download_by_url(
                    item.video_url, folder=download_path))
        return paths

    def download_highlights_from_url(self, url):
        return self.download_highlight(self.client.highlight_pk_from_url(url))


class TestInstagramTools(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestInstagramTools, self).__init__(*args, **kwargs)
        self.ig_tools = InstagramTools('username', 'password')

    def test_extract_username(self):
        self.assertRaises(
            UserNotFound, InstagramTools.extract_username, '//')
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
