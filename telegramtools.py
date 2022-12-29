import os
import shutil
from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          CallbackContext)


def archive_folder(folder, path):
    shutil.make_archive(path, 'zip', folder)


class TelegramTools:
    def __init__(self, bot_token, ig_tools):
        self.ig_tools = ig_tools
        self.updater = Updater(bot_token)
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(CommandHandler("start", self.help_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))

        self.dispatcher.add_handler(MessageHandler(
            Filters.text & ~Filters.command, self.echo))

        self.updater.start_polling()
        self.updater.idle()

    def help_command(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text(
            "Send me an username and I will send you an archived profile!")

    def echo(self, update: Update, context: CallbackContext) -> None:
        print(update.message.text)
        target_user = update.message.text

        if os.path.isdir(target_user):
            shutil.rmtree(target_user)

        if os.path.isfile(target_user + ".zip"):
            os.remove(target_user + ".zip")

        os.mkdir(target_user)

        self.ig_tools.download_all_profile_media(target_user, target_user)
        archive_folder(target_user, target_user)

        if os.path.isfile(target_user + ".zip"):
            update.message.reply_text("Here is your archive")
            with open(target_user + ".zip", 'rb') as p:
                update.message.reply_document(p)
        else:
            update.message.reply_text("Wooops, some problem is here...")

        if os.path.isdir(target_user):
            shutil.rmtree(target_user)

        if os.path.isfile(target_user + ".zip"):
            os.remove(target_user + ".zip")
