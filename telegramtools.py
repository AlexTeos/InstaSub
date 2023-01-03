import os
import shutil
from telegram import Update, Bot
from telegram.ext import (Updater, CommandHandler, CallbackContext)

from instagramtools import (PrivateAccountException, InvalidUsername,
                            MediaNotFound)


class TelegramTools:
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
            media_path = self.ig_tools.download_media_from_url(request)
            reply_message.edit_text(text='Here is your media')
            with open(media_path, 'rb') as document:
                update.message.reply_document(document)
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

            if os.path.isdir(user_id):
                shutil.rmtree(user_id)

            os.mkdir(user_id)
            i = 1
            for m in medias:
                self.ig_tools.download_media(m, user_id)
                msg_text = '{0} medias out of {1} have already been downloaded'.format(
                    i, len(medias))
                reply_message.edit_text(text=msg_text)
                i = i + 1

            archive_file = user_id + '.zip'

            if os.path.isfile(archive_file):
                os.remove(archive_file)

            shutil.make_archive(user_id, 'zip', user_id)

            shutil.rmtree(user_id)

            reply_message.edit_text(text='Here is your archive')
            with open(archive_file, 'rb') as document:
                update.message.reply_document(document)

            os.remove(archive_file)

        except IndexError:
            update.message.reply_text(
                'Usage: /download_profile instagram_user_name')
        except PrivateAccountException:
            reply_message.edit_text('The account is private')
        except InvalidUsername:
            reply_message.edit_text('Invalid link or username')
