import html
import json
import logging
import os
import shutil
import traceback
import zipfile
from time import sleep

from aiostream import stream
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.constants import ParseMode
from telegram.error import (TimedOut, TelegramError)
from telegram.ext import (Application, CommandHandler, ContextTypes, filters,
                          MessageHandler)

from instagramtools import (PrivateAccountException, UserNotFound,
                            MediaNotFound, HighlightNotFound)


async def timeout_retry(attempts, func, *args, **kwargs):
    for i in range(attempts):
        try:
            result = await func(*args, **kwargs)
        except TimedOut as err:
            exception = err
        except Exception as err:
            raise err
        else:
            return result
    raise exception


class TelegramTools:
    FILE_SIZE_LIMIT = 48 * 1024 * 1024

    def __init__(self, bot_token, admin_id, ig_tools):
        self.logger = logging.getLogger('instasub')
        self.ig_tools = ig_tools
        self.admin_id = admin_id
        self.logger.info('Sign in to telegram bot: id - {0}'.format(bot_token))
        self.application = Application.builder().token(bot_token).concurrent_updates(True).build()
        self.application.add_handler(CommandHandler('start', self.help_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.resolve_command))
        self.application.add_error_handler(self.error_handler)

        while True:
            try:
                self.application.run_polling()
            except TelegramError as e:
                self.logger.error('Telegram error occurred:', e.message)
                self.notify_admin(e.message)
            except Exception as e:
                self.logger.error('Exception occurred:', e)
                self.notify_admin(str(e))
            sleep(1)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.logger.error(msg='Exception while handling an update:', exc_info=context.error)

        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = ''.join(tb_list)

        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f'An exception was raised while handling an update\n'
            f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
            '</pre>\n\n'
            f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
            f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
            f'<pre>{html.escape(tb_string)}</pre>'
        )

        await context.bot.send_message(
            chat_id=self.admin_id, text=message, parse_mode=ParseMode.HTML
        )

    async def notify_admin(self, message):
        self.application.bot.send_message(self.admin_id, message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await timeout_retry(3, update.message.reply_text,
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
                await timeout_retry(3, update.message.reply_text,
                                    'I don\'t know what to do with that. Try something else')

    async def download_story(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            reply_message = await timeout_retry(3, update.message.reply_text, 'Downloading story...')
            download_path = str(update.update_id) + '/'
            story_path = self.ig_tools.download_story_from_url(update.message.text, download_path)
            await timeout_retry(3, reply_message.edit_text, 'Here is your story')
            if str(story_path).endswith('.mp4'):
                await timeout_retry(3, update.message.reply_video, open(story_path, 'rb'))
            else:
                await timeout_retry(3, update.message.reply_photo, open(story_path, 'rb'))

            if os.path.exists(download_path):
                shutil.rmtree(download_path)

            self.logger.debug(
                'Story request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                update.message.text))
        except MediaNotFound:
            self.logger.debug(
                'Story request from {0} was not completed - story not found: {1}'.format(update.message.from_user.id,
                                                                                         update.message.text))
            await timeout_retry(3, reply_message.edit_text, 'Story not found')

    async def download_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            reply_message = await timeout_retry(3, update.message.reply_text, 'Downloading media...')
            download_path = str(update.update_id) + '/'
            media_paths = self.ig_tools.download_media_from_url(update.message.text, download_path)
            medias = []
            for media_path in media_paths:
                if str(media_path).endswith('.mp4'):
                    medias.append(InputMediaVideo(media=open(media_path, 'rb')))
                else:
                    medias.append(InputMediaPhoto(media=open(media_path, 'rb')))
            await timeout_retry(3, reply_message.edit_text, 'Here is your media')
            caption = self.ig_tools.get_media_info_from_url(update.message.text)
            # if len(caption) > 1024:
            if True:
                await timeout_retry(3, update.message.reply_media_group, medias)
                await timeout_retry(3, update.message.reply_text, caption)
            # else:
            #    await timeout_retry(3, update.message.reply_media_group, media=medias, caption=caption)

            if os.path.exists(download_path):
                shutil.rmtree(download_path)

            self.logger.debug(
                'Media request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                update.message.text))
        except MediaNotFound:
            self.logger.debug(
                'Media request from {0} was not completed - media not found: {1}'.format(update.message.from_user.id,
                                                                                         update.message.text))
            await timeout_retry(3, reply_message.edit_text, 'Media not found')

    async def download_highlight(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            reply_message = await timeout_retry(3, update.message.reply_text, 'Downloading highlight...')
            download_path = str(update.update_id) + '/'
            highlight_paths = self.ig_tools.download_highlights_from_url(update.message.text, download_path)
            await timeout_retry(3, reply_message.edit_text, 'Here is your highlights')
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
                    await timeout_retry(3, update.message.reply_media_group, highlights)
                    highlights = []
                    highlight_counter = 0

            if os.path.exists(download_path):
                shutil.rmtree(download_path)

            self.logger.debug(
                'Highlight request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                    update.message.text))
        except HighlightNotFound:
            self.logger.debug(
                'Highlight request from {0} was not completed - highlight not found: {1}'.format(
                    update.message.from_user.id,
                    update.message.text))
            await timeout_retry(3, reply_message.edit_text, 'Highlight not found')

    class SplitArchiver:
        file = None
        counter = 1
        size = 0
        __SIZE_LIMIT = 0
        base_name = None

        def __init__(self, base_name, work_dir, file_size_limit):
            self.base_name = base_name
            self.__SIZE_LIMIT = file_size_limit
            self.work_dir = work_dir
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
                self.file = zipfile.ZipFile(self.work_dir + self.base_name + '_' + str(self.counter) + '.zip', 'w')

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

    async def download_medias(self, user_id, path):
        medias = self.ig_tools.get_user_medias(user_id)
        for media in medias:
            try:
                download_path = path + 'media/' + media.taken_at.strftime("%d.%m.%y %H-%M-%S") + '/'
                info_file = self.save_to_file(
                    self.ig_tools.get_media_info(media) + self.ig_tools.get_media_comments(media),
                    download_path + media.pk + '.txt')
                yield info_file
                files = self.ig_tools.download_media(media, download_path)
                for file in files:
                    yield file
            except Exception as e:
                self.logger.error('During media download exception occurred:', str(e))
                self.notify_admin('During media download exception occurred:' + str(e))

    async def download_tagged_medias(self, user_id, path):
        tagged_medias = self.ig_tools.get_user_tagged_medias(user_id)
        for tagged_media in tagged_medias:
            download_path = path + 'tagged_media/' + tagged_media.taken_at.strftime(
                "%d.%m.%y %H-%M-%S") + '/'
            info_file = self.save_to_file(
                self.ig_tools.get_media_info(tagged_media) + self.ig_tools.get_media_comments(tagged_media),
                download_path + tagged_media.pk + '.txt')
            yield info_file
            files = self.ig_tools.download_media(tagged_media, download_path)
            for file in files:
                yield file

    async def download_highlights(self, user_id, path):
        highlights = self.ig_tools.get_highlights(user_id)
        for highlight in highlights:
            download_path = path + 'highlights/' + highlight.created_at.strftime(
                "%d.%m.%y %H-%M-%S") + '/'
            info_file = self.save_to_file(self.ig_tools.get_highlight_info(highlight),
                                          download_path + highlight.pk + '.txt')
            yield info_file
            files = self.ig_tools.download_highlight(highlight, download_path)
            for file in files:
                yield file

    async def download_user_info(self, user_id, path):
        yield self.save_to_file(self.ig_tools.get_user_info(user_id), path + 'user_info.txt')
        yield self.ig_tools.get_user_pic(user_id, path)

    async def download_profile_medias(self, user_id, path):
        combine = stream.merge(self.download_user_info(user_id, path), self.download_medias(user_id, path),
                               self.download_tagged_medias(user_id, path), self.download_highlights(user_id, path))

        async with combine.stream() as streamer:
            async for item in streamer:
                yield item

    async def download_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.ig_tools.set_delay(True)
        try:
            self.logger.debug(
                'Starting to download account {0} requested by {1}'.format(update.message.text,
                                                                           update.message.from_user.id))

            reply_message = await timeout_retry(3, update.message.reply_text, 'Checking user...')
            user_id = self.ig_tools.get_user_id(update.message.text)
            download_path = str(update.update_id) + '/'
            archiver = self.SplitArchiver(update.message.text, download_path, self.FILE_SIZE_LIMIT)

            i = 0
            async for file in self.download_profile_medias(user_id, download_path):
                archive = archiver.write(file, os.path.relpath(file, download_path))
                if archive:
                    await timeout_retry(3, update.message.reply_document, open(archive, 'rb'))
                    os.remove(archive)
                i = i + 1
                try:
                    await timeout_retry(1, reply_message.edit_text, '{0} medias were downloaded'.format(i))
                except TimedOut:
                    pass

            archive = archiver.close()
            if archive:
                await timeout_retry(3, update.message.reply_document, open(archive, 'rb'))
                os.remove(archive)

            if os.path.exists(download_path):
                shutil.rmtree(download_path)

            await timeout_retry(3, reply_message.edit_text, 'Account download completed')

            self.logger.debug(
                'Account download request from {0} was completed successfully: {1}'.format(update.message.from_user.id,
                                                                                           update.message.text))
        except PrivateAccountException:
            self.logger.debug('Requested account {0} is private, request from {1} '.format(update.message.text,
                                                                                           update.message.from_user.id))
            await timeout_retry(3, reply_message.edit_text, 'The account is private')
        except UserNotFound:
            self.logger.debug('Requested account {0} does not exits, request from {1} '.format(update.message.text,
                                                                                               update.message.from_user.id))
            await timeout_retry(3, reply_message.edit_text, 'Invalid link or username')
            raise

        self.ig_tools.set_delay(False)
