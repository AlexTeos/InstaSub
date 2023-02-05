import os
import shutil
import zipfile
import logging
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import (Application, CommandHandler, ContextTypes, filters,
                          MessageHandler)
from instagramtools import (PrivateAccountException, UserNotFound,
                            MediaNotFound, HighlightNotFound)


class TelegramTools:
    FILE_SIZE_LIMIT = 48 * 1024 * 1024

    def __init__(self, bot_token, ig_tools):
        self.logger = logging.getLogger('instasub')
        self.ig_tools = ig_tools
        self.logger.info('Sing in to telegram bot: id - {0}'.format(bot_token))
        self.application = Application.builder().token(bot_token).build()
        self.application.add_handler(CommandHandler('start', self.help_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.resolve_command))

        self.application.run_polling()

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            'Send me an username and I will send you an archived profile! Also you can send me a link to a story, post or highlight!')

    async def resolve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.logger.info('New request from {0}: {1}'.format(update.message.from_user.id, update.message.text))
        if '/highlights/' in update.message.text:
            return await self.download_highlight(update, context)
        elif '/stories/' in update.message.text:
            return await self.download_story(update, context)
        elif '/p/' in update.message.text or '/reel/' in update.message.text:
            return await self.download_media(update, context)
        else:
            try:
                return await self.download_profile(update, context)
            except UserNotFound:
                self.logger.warning(
                    'Unrecognized request from {0}: {1}'.format(update.message.from_user.id, update.message.text))
                reply_message = update.message.reply_text('I don\'t know what to do with that. Try something else')

    async def download_story(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            reply_message = await update.message.reply_text('Downloading story...')
            story_path = self.ig_tools.download_story_from_url(update.message.text)
            await reply_message.edit_text('Here is your story')
            if str(story_path).endswith('.mp4'):
                await update.message.reply_video(open(story_path, 'rb'))
            else:
                await update.message.reply_photo(open(story_path, 'rb'))

            os.remove(story_path)

            self.logger.debug(
                'Story request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                update.message.text))
        except MediaNotFound:
            self.logger.debug(
                'Story request from {0} was not completed - story not found: {1}'.format(update.message.from_user.id,
                                                                                         update.message.text))
            await reply_message.edit_text('Story not found')

    async def download_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            reply_message = await update.message.reply_text('Downloading media...')
            media_paths = self.ig_tools.download_media_from_url(update.message.text)
            medias = []
            for media_path in media_paths:
                if str(media_path).endswith('.mp4'):
                    medias.append(InputMediaVideo(media=open(media_path, 'rb')))
                else:
                    medias.append(InputMediaPhoto(media=open(media_path, 'rb')))
            await reply_message.edit_text('Here is your media')
            caption = self.ig_tools.get_media_info_from_url(update.message.text)
            if len(caption) > 1024:
                await update.message.reply_media_group(medias)
                await update.message.reply_text(caption)
            else:
                await update.message.reply_media_group(media=medias, caption=caption)

            for media_path in media_paths:
                os.remove(media_path)

            self.logger.debug(
                'Media request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                update.message.text))
        except MediaNotFound:
            self.logger.debug(
                'Media request from {0} was not completed - media not found: {1}'.format(update.message.from_user.id,
                                                                                         update.message.text))
            await reply_message.edit_text('Media not found')

    async def download_highlight(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            reply_message = await update.message.reply_text('Downloading highlight...')
            highlight_paths = self.ig_tools.download_highlights_from_url(update.message.text)
            await reply_message.edit_text('Here is your highlights')
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
                    await update.message.reply_media_group(highlights)
                    highlights = []
                    highlight_counter = 0

            for highlight_path in highlight_paths:
                os.remove(highlight_path)

            self.logger.debug(
                'Highlight request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                    update.message.text))
        except HighlightNotFound:
            self.logger.debug(
                'Highlight request from {0} was not completed - highlight not found: {1}'.format(
                    update.message.from_user.id,
                    update.message.text))
            await reply_message.edit_text('Highlight not found')

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

    def save_to_file(self, str, path) -> str:
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, "w+", encoding="utf-8") as info_file:
            info_file.write(str)
        return path

    async def gen_input(self, user_id):
        # Media
        medias = self.ig_tools.get_user_medias(user_id)
        for media in medias:
            download_path = user_id + '/media/' + media.taken_at.strftime("%d.%m.%y %H-%M-%S") + '/'
            info_file = self.save_to_file(
                self.ig_tools.get_media_info(media) + self.ig_tools.get_media_comments(media),
                download_path + media.pk + '.txt')
            yield info_file
            files = self.ig_tools.download_media(media, download_path)
            for file in files:
                yield file

        # self.logger.debug(
        #    '{0}\'s medias downloaded successfully: {1}'.format(update.message.text, update.message.from_user.id))

        # Tagged media
        tagged_medias = self.ig_tools.get_user_tagged_medias(user_id)
        for tagged_media in tagged_medias:
            download_path = user_id + '/tagged_media/' + tagged_media.taken_at.strftime("%d.%m.%y %H-%M-%S") + '/'
            info_file = self.save_to_file(
                self.ig_tools.get_media_info(tagged_media) + self.ig_tools.get_media_comments(tagged_media),
                download_path + tagged_media.pk + '.txt')
            yield info_file
            files = self.ig_tools.download_media(tagged_media, download_path)
            for file in files:
                yield file

        # self.logger.debug(
        #    '{0}\'s tagged medias downloaded successfully: {1}'.format(update.message.text,
        #                                                               update.message.from_user.id))

        # Highlight
        highlights = self.ig_tools.get_highlights(user_id)
        for highlight in highlights:
            download_path = user_id + '/highlights/' + highlight.created_at.strftime(
                "%d.%m.%y %H-%M-%S") + '/'
            info_file = self.save_to_file(self.ig_tools.get_highlight_info(highlight),
                                          download_path + highlight.pk + '.txt')
            yield info_file
            files = self.ig_tools.download_highlight(highlight, download_path)
            for file in files:
                yield file

        # self.logger.debug(
        #    '{0}\'s highlights downloaded successfully: {1}'.format(update.message.text,
        #                                                            update.message.from_user.id))

    async def download_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            self.logger.debug(
                'Starting to download account {0} requested by {1}'.format(update.message.text,
                                                                           update.message.from_user.id))

            reply_message = await update.message.reply_text('Checking user...')
            user_id = self.ig_tools.get_user_id(update.message.text)
            archiver = self.SplitArchiver(user_id, self.FILE_SIZE_LIMIT)

            async for file in self.gen_input(user_id):
                archive = archiver.write(file, os.path.relpath(file, user_id))
                if archive:
                    await update.message.reply_document(open(archive, 'rb'))
                    os.remove(archive)

            archive = archiver.close()
            if archive:
                await update.message.reply_document(open(archive, 'rb'))
                os.remove(archive)

            if os.path.exists(user_id):
                shutil.rmtree(user_id)

            self.logger.debug(
                'Account download request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                           update.message.text))
        except PrivateAccountException:
            self.logger.debug('Requested account {0} is private, request from {1} '.format(update.message.text,
                                                                                           update.message.from_user.id))
            await reply_message.edit_text('The account is private')
        except UserNotFound:
            self.logger.debug('Requested account {0} does not exits, request from {1} '.format(update.message.text,
                                                                                               update.message.from_user.id))
            await reply_message.edit_text('Invalid link or username')
            raise
