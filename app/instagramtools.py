import unittest
import os
import logging
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (LoginRequired, MediaNotFound,
                                   HighlightNotFound, UserNotFound)


class PrivateAccountException(Exception):
    "You are trying to interract with a private user"


class InstagramTools:
    def __init__(self, username, password):
        self.logger = logging.getLogger('instasub')
        self.client = Client()
        self.logger.info('Sing in to instagram: username - {0} password - {1}'.format(username, password))
        credential_file = '/ext/credential.json'
        if os.path.exists(credential_file):
            self.client.load_settings(credential_file)
            self.client.login(username, password)
        else:
            self.client.login(username, password)
            self.client.dump_settings(credential_file)

        try:
            self.client.account_info()
        except LoginRequired:
            self.logger.warning('Relogin to instagram')
            self.client.relogin()
            self.client.dump_settings(credential_file)

    @staticmethod
    def extract_username(username):
        username = username.split('/')
        while '' in username:
            username.remove('')

        if len(username) == 0:
            raise UserNotFound

        return username.pop()

    def get_user_id(self, username) -> str:
        self.logger.debug('Get user id: {0}'.format(username))
        return self.client.user_id_from_username(self.extract_username(username))

    def get_user_medias(self, user_id):
        self.logger.debug('Get user media: {0}'.format(user_id))
        if not self.is_public_account(user_id):
            raise PrivateAccountException
        return self.client.user_medias(user_id)

    def get_user_tagged_medias(self, user_id):
        self.logger.debug('Get user tagged media: {0}'.format(user_id))
        if not self.is_public_account(user_id):
            raise PrivateAccountException
        return self.client.usertag_medias(user_id)

    def is_public_account(self, user_id):
        self.logger.debug('Check account privacy: {0}'.format(user_id))
        user = self.client.user_info(user_id)
        return not user.is_private

    def download_media(self, media, path='./') -> list:
        self.logger.debug('Download media: {0}'.format(media))
        if not os.path.exists(path):
            os.makedirs(path)
        if media.media_type == 1:
            return [self.client.photo_download(media.pk, path)]
        elif media.media_type == 2:
            return [self.client.video_download(media.pk, path)]
        elif media.media_type == 8:
            return self.client.album_download(media.pk, path)

    def download_media_from_url(self, url) -> list:
        self.logger.debug('Download media: {0}'.format(url))
        media_pk = self.client.media_pk_from_url(url)
        media = self.client.media_info(media_pk)
        return self.download_media(media)

    def get_media_info_from_url(self, url) -> str:
        self.logger.debug('Get media info: {0}'.format(url))
        media_pk = self.client.media_pk_from_url(url)
        media = self.client.media_info(media_pk)
        return self.get_media_info(media)

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

    def download_story_from_url(self, url) -> Path:
        self.logger.debug('Download story: {0}'.format(url))
        return self.client.story_download(self.client.story_pk_from_url(url))

    def get_highlights(self, user_id) -> list:
        self.logger.debug('Get user highlights: {0}'.format(user_id))
        return self.client.user_highlights(user_id)

    def get_highlight_info(self, highlight, path='./') -> str:
        self.logger.debug('Get highlight info: {0}'.format(highlight))
        info = 'User: ' + highlight.user.username
        if highlight.user.full_name:
            info = info + ' - ' + highlight.user.full_name
        info = info + '\nTitle: ' + highlight.title
        info = info + '\nCreated at: ' + highlight.created_at.strftime("%d.%m.%y %H:%M:%S")
        return info

    def download_highlight(self, highlight, path='./') -> list:
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

    def download_highlights_from_url(self, url):
        self.logger.debug('Download highlight: {0}'.format(url))
        return self.download_highlight(self.client.highlight_info(self.client.highlight_pk_from_url(url)))


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
