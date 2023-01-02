import os
import shutil
from telegram import Update, Bot
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          CallbackContext)


def archive_folder(path):
    shutil.make_archive(path, 'zip', path)


class TelegramTools:
    def __init__(self, bot_token, ig_tools):
        self.ig_tools = ig_tools
        self.bot = Bot(bot_token)
        self.updater = Updater(bot_token)
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(CommandHandler('start', self.help_command))
        self.dispatcher.add_handler(CommandHandler('help', self.help_command))

        self.dispatcher.add_handler(MessageHandler(
            Filters.text & ~Filters.command, self.echo))

        self.updater.start_polling()
        self.updater.idle()

    def help_command(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text(
            'Send me an username and I will send you an archived profile!')

    def echo(self, update: Update, context: CallbackContext) -> None:
        reply_message = update.message.reply_text('Checking user...')
        user_id = self.ig_tools.get_user_id(update.message.text)

        if user_id and self.ig_tools.is_public_user(user_id):
            medias = self.ig_tools.get_medias(user_id)
            if medias:
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

                archive_folder(user_id)

                if os.path.isdir(user_id):
                    shutil.rmtree(user_id)

            if os.path.isfile(archive_file):
                reply_message.edit_text(text='Here is your archive')
                with open(archive_file, 'rb') as p:
                    update.message.reply_document(p)

                if os.path.isfile(archive_file):
                    os.remove(archive_file)

            return

        update.message.reply_text('Wooops, some problem is here...')
