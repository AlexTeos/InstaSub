import os
import zipfile
from telegram import Update, Bot, InputMediaPhoto, InputMediaVideo
from telegram.ext import (Updater, CommandHandler, CallbackContext)
from instagramtools import (PrivateAccountException, InvalidUsername,
                            MediaNotFound)


class TelegramTools:
    FILE_SIZE_LIMIT = 50 * 1024 * 1024
    def __init__(self, bot_token, ig_tools):
        self.ig_tools = ig_tools
        self.bot = Bot(bot_token)
        self.updater = Updater(bot_token)
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(CommandHandler('start', self.help_command))
        self.dispatcher.add_handler(CommandHandler('help', self.help_command))
        self.dispatcher.add_handler(CommandHandler(
            'download_profile', self.download_profile))
        self.dispatcher.add_handler(CommandHandler(
            'download_media', self.download_media))

        self.updater.start_polling()
        self.updater.idle()

    def help_command(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text(
            'Send me an username and I will send you an archived profile!')

    def download_media(self, update: Update, context: CallbackContext) -> None:
        try:
            request = context.args[0]
            reply_message = update.message.reply_text('Downloading media...')
            media_paths = self.ig_tools.download_media_from_url(request)
            medias = []
            for media_path in media_paths:
                if str(media_path).endswith('.mp4'):
                    medias.append(InputMediaVideo(
                        media=open(media_path, 'rb')))
                else:
                    medias.append(InputMediaPhoto(
                        media=open(media_path, 'rb')))
            reply_message.edit_text(text='Here is your media')
            update.message.reply_media_group(medias)

            for media_path in media_paths:
                os.remove(media_path)

        except IndexError:
            update.message.reply_text('Usage: /download_media link_to_media')
        except MediaNotFound:
            reply_message.edit_text('Media not found')

    def download_profile(self, update: Update, context: CallbackContext) -> None:
        try:
            request = context.args[0]
            reply_message = update.message.reply_text('Checking user...')
            user_id = self.ig_tools.get_user_id(request)

            medias = self.ig_tools.get_medias(user_id)

            if len(medias) == 0:
                update.message.reply_text('User don\'t have any media')
                return None

            archive_name = None
            archive_file = None
            media_counter = 1
            archive_counter = 1
            size_sum = 0
            for media in medias:
                files = self.ig_tools.download_media(media)
                for file in files:
                    file_size = os.stat(file).st_size
                    if file_size >= self.FILE_SIZE_LIMIT:
                        os.remove(file)
                        continue

                    if file_size + size_sum >= self.FILE_SIZE_LIMIT:
                        archive_file.close()
                        with open(archive_name, 'rb') as document:
                            update.message.reply_document(document)
                        os.remove(archive_name)
                        archive_name = None
                        archive_counter = archive_counter + 1
                        size_sum = 0

                    if archive_name is None:
                        archive_name = user_id + '_' + \
                            str(archive_counter) + '.zip'
                        archive_file = zipfile.ZipFile(archive_name, 'w')

                    archive_file.write(file.name)
                    size_sum += file_size
                    os.remove(file)
                msg_text = '{0} posts out of {1} have been downloaded'.format(
                    media_counter, len(medias))
                reply_message.edit_text(text=msg_text)
                media_counter = media_counter + 1

            if archive_name and archive_file:
                archive_file.close()
                with open(archive_name, 'rb') as document:
                    update.message.reply_document(document)
                os.remove(archive_name)

            reply_message.edit_text(text='Download completed with {0} posts and {1} archives'.format(
                media_counter - 1, archive_counter))

        except IndexError:
            update.message.reply_text(
                'Usage: /download_profile instagram_user_name')
        except PrivateAccountException:
            reply_message.edit_text('The account is private')
        except InvalidUsername:
            reply_message.edit_text('Invalid link or username')
