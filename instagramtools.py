import os
from instagrapi import Client


class InstagramTools:
    def __init__(self, username, password):
        self.client = Client()

        if os.path.exists('credential.json'):
            self.client.load_settings('credential.json')
            self.client.login(username, password)
        else:
            self.client.login(username, password)
            self.client.dump_settings('credential.json')

    def download_all_profile_media(self, username, path):
        user_id = self.client.user_id_from_username(username)
        medias = self.client.user_medias(user_id)

        for m in medias:
            if m.media_type == 1:
                # Photo
                self.client.photo_download(m.pk, path)
            elif m.media_type == 2 and m.product_type == 'feed':
                # Video
                self.client.video_download(m.pk, path)
            elif m.media_type == 2 and m.product_type == 'igtv':
                # IGTV
                self.client.video_download(m.pk, path)
            elif m.media_type == 2 and m.product_type == 'clips':
                # Reels
                self.client.video_download(m.pk, path)
            elif m.media_type == 8:
                # Album
                self.client.album_download(m.pk, path)
