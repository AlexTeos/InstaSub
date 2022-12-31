import unittest
import os
import shutil
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired
)


def archive_folder(path):
    shutil.make_archive(path, 'zip', path)


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

        if len(username):
            return username.pop()

    def get_medias(self, username):
        username = self.extract_username(username)
        if username:
            user_id = self.client.user_id_from_username(username)
            return self.client.user_medias(user_id)

    def download_media(self, media, path):
        if media.media_type == 1:
            # Photo
            self.client.photo_download(media.pk, path)
        elif media.media_type == 2 and media.product_type == 'feed':
            # Video
            self.client.video_download(media.pk, path)
        elif media.media_type == 2 and media.product_type == 'igtv':
            # IGTV
            self.client.video_download(media.pk, path)
        elif media.media_type == 2 and media.product_type == 'clips':
            # Reels
            self.client.video_download(media.pk, path)
        elif media.media_type == 8:
            # Album
            self.client.album_download(media.pk, path)

    def download_all_profile_media(self, username):
        medias = self.get_medias(username)

        if medias:
            if os.path.isdir(username):
                shutil.rmtree(username)

            os.mkdir(username)

            for m in medias:
                self.download_media(m, username)

            archive_file = username + ".zip"

            if os.path.isfile(archive_file):
                os.remove(archive_file)

            archive_folder(username)

            if os.path.isdir(username):
                shutil.rmtree(username)

            return archive_file

        return None


class TestInstagramTools(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestInstagramTools, self).__init__(*args, **kwargs)
        self.ig_tools = InstagramTools('username', 'password')

    def test_extract_username(self):
        self.assertEqual(InstagramTools.extract_username(
            '//'), None)
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

    def test_download_all_profile_media(self):
        self.assertEqual(self.ig_tools.download_all_profile_media(
            'https://www.instagram.com/username/'), 'username.zip')


if __name__ == '__main__':
    unittest.main()
