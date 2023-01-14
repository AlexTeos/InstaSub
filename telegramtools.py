import os
import shutil
import zipfile
from telegram import Update, Bot, InputMediaPhoto, InputMediaVideo
from telegram.ext import (Updater, CommandHandler, CallbackContext, Filters,
                          MessageHandler)
from instagramtools import (PrivateAccountException, UserNotFound,
                            MediaNotFound, HighlightNotFound)


class TelegramTools:
    FILE_SIZE_LIMIT = 50 * 1024 * 1024

    def __init__(self, bot_token, ig_tools):
        self.ig_tools = ig_tools
        self.bot = Bot(bot_token)
        self.updater = Updater(bot_token)
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(CommandHandler('start', self.help_command))
        self.dispatcher.add_handler(CommandHandler('help', self.help_command))
        self.dispatcher.add_handler(MessageHandler(
            Filters.text & ~Filters.command, self.resolve_command))

        self.updater.start_polling()
        self.updater.idle()

    def help_command(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text(
            'Send me an username and I will send you an archived profile!')

    def resolve_command(self, update: Update, context: CallbackContext) -> None:
        if '/highlights/' in update.message.text:
            return self.download_highlight(update, context)
        elif '/stories/' in update.message.text:
            return self.download_story(update, context)
        elif '/p/' in update.message.text or '/reel/' in update.message.text:
            return self.download_media(update, context)
        else:
            try:
                return self.download_profile(update, context)
            except UserNotFound:
                reply_message = update.message.reply_text(
                    'I don\'t know what to do with that. Try something else')

    def download_story(self, update: Update, context: CallbackContext) -> None:
        try:
            reply_message = update.message.reply_text('Downloading story...')
            story_path = self.ig_tools.download_story_from_url(update.message.text)
            reply_message.edit_text('Here is your story')
            if str(story_path).endswith('.mp4'):
                update.message.reply_video(open(story_path, 'rb'))
            else:
                update.message.reply_photo(open(story_path, 'rb'))

            os.remove(story_path)
        except MediaNotFound:
            reply_message.edit_text('Story not found')

    def download_media(self, update: Update, context: CallbackContext) -> None:
        try:
            reply_message = update.message.reply_text('Downloading media...')
            media_paths = self.ig_tools.download_media_from_url(update.message.text)
            medias = []
            for media_path in media_paths:
                if str(media_path).endswith('.mp4'):
                    medias.append(InputMediaVideo(media=open(media_path, 'rb')))
                else:
                    medias.append(InputMediaPhoto(media=open(media_path, 'rb')))
            reply_message.edit_text('Here is your media')
            update.message.reply_media_group(medias)

            for media_path in media_paths:
                os.remove(media_path)

        except MediaNotFound:
            reply_message.edit_text('Media not found')

    def download_highlight(self, update: Update, context: CallbackContext) -> None:
        try:
            reply_message = update.message.reply_text('Downloading highlight...')
            highlight_paths = self.ig_tools.download_highlights_from_url(update.message.text)
            reply_message.edit_text('Here is your highlights')
            highlights = []
            highlight_counter = 0
            highlight_index = 0
            for highlight_path in highlight_paths:
                if str(highlight_path).endswith('.mp4'):
                    highlights.append(InputMediaVideo(media=open(highlight_path, 'rb')))
                else:
                    highlights.append(InputMediaPhoto(media=open(highlight_path, 'rb')))

                highlight_counter = highlight_counter + 1
                highlight_index = highlight_index + 1

                if highlight_counter == 10 or highlight_index == len(highlight_paths):
                    update.message.reply_media_group(highlights)
                    highlights = []
                    highlight_counter = 0

            for highlight_path in highlight_paths:
                os.remove(highlight_path)

        except HighlightNotFound:
            reply_message.edit_text('Highlight not found')

    class SplitArchiver:
        file = None
        counter = 1
        size = 0
        __SIZE_LIMIT = 0
        base_name = None

        def __init__(self, base_name, file_size_limit):
            self.base_name = base_name
            self.__SIZE_LIMIT = file_size_limit
            pass

        def write(self, file, path) -> str:
            name = None
            file_size = os.stat(file).st_size
            if file_size >= self.__SIZE_LIMIT:
                os.remove(file)
                return None

            if file_size + self.size >= self.__SIZE_LIMIT:
                name = self.close()

            if self.file is None:
                self.file = zipfile.ZipFile(self.base_name + '_' + str(self.counter) + '.zip', 'w')

            self.file.write(file, path)
            self.size += file_size
            os.remove(file)

            return name

        def close(self) -> str:
            if self.file:
                self.file.close()
                name = self.file.filename
                self.file = None
                if self.size:
                    self.counter = self.counter + 1
                    self.size = 0
                    return name
            return None

    def download_profile(self, update: Update, context: CallbackContext) -> None:
        try:
            reply_message = update.message.reply_text('Checking user...')
            user_id = self.ig_tools.get_user_id(update.message.text)
            archiver = self.SplitArchiver(user_id, self.FILE_SIZE_LIMIT)

            # Media
            medias = self.ig_tools.get_user_medias(user_id)
            media_counter = 0
            for media in medias:
                files = self.ig_tools.download_media(media, user_id + '/media/')
                for file in files:
                    archive = archiver.write(file, os.path.relpath(file, user_id))
                    if archive:
                        update.message.reply_document(open(archive, 'rb'))
                        os.remove(archive)
                reply_message.edit_text(
                    '{0} posts out of {1} have been downloaded'.format(media_counter + 1, len(medias)))
                media_counter = media_counter + 1

            # Tagged media
            tagged_medias = self.ig_tools.get_user_tagged_medias(user_id)
            tagged_media_counter = 0
            for tagged_media in tagged_medias:
                files = self.ig_tools.download_media(tagged_media, user_id + '/tagged_media/')
                for file in files:
                    archive = archiver.write(file, os.path.relpath(file, user_id))
                    if archive:
                        update.message.reply_document(open(archive, 'rb'))
                        os.remove(archive)
                reply_message.edit_text(
                    '{0} tagged posts out of {1} have been downloaded'.format(tagged_media_counter + 1,
                                                                              len(tagged_medias)))
                tagged_media_counter = tagged_media_counter + 1

            # Highlight
            highlights = self.ig_tools.get_highlights(user_id)
            highlight_counter = 0
            for highlight in highlights:
                files = self.ig_tools.download_highlight(highlight.pk, user_id + '/highlights/')
                for file in files:
                    archive = archiver.write(file, os.path.relpath(file, user_id))
                    if archive:
                        update.message.reply_document(open(archive, 'rb'))
                        os.remove(archive)
                reply_message.edit_text(
                    '{0} highlights out of {1} have been downloaded'.format(highlight_counter + 1, len(highlights)))
                highlight_counter = highlight_counter + 1

            if media_counter + highlight_counter + tagged_media_counter == 0:
                reply_message.edit_text('User don\'t have any media')
                return None

            archive = archiver.close()
            if archive:
                update.message.reply_document(open(archive, 'rb'))
                os.remove(archive)

            if os.path.exists(user_id):
                shutil.rmtree(user_id)

            reply_message.edit_text('Download completed with {0} posts & highlights and {1} archives'.format(
                media_counter + tagged_media_counter + highlight_counter, archiver.archive_counter))

        except PrivateAccountException:
            reply_message.edit_text('The account is private')
        except UserNotFound:
            reply_message.edit_text('Invalid link or username')
            raise
