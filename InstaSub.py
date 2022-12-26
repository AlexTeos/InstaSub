import os
import shutil
from pathlib import Path
import argparse
from instagrapi import Client
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    
def archive_folder(folder, path):
    shutil.make_archive(path, 'zip', folder)
    
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
            paths = []
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
            pass

class TelegramTools:
    def __init__(self, bot_token, ig_tools):
        self.ig_tools = ig_tools
        self.application = Application.builder().token(bot_token).build()
    
        self.application.add_handler(CommandHandler("start", self.help_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
    
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))
    
        self.application.run_polling()
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Send me an username and I will send you an archived profile!")
    
    
    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(update.message.text)
        target_user = update.message.text
        if os.path.isdir(target_user):
            shutil.rmtree(target_user)
            
        if os.path.isfile(target_user + ".zip") :
            os.remove(target_user + ".zip")
            
        os.mkdir(target_user)
        
        self.ig_tools.download_all_profile_media(target_user, target_user)
        archive_folder(target_user, target_user)
        
        if os.path.isfile(target_user + ".zip") :
            await update.message.reply_text("Here is your archive")
            p = Path(target_user + ".zip")
            await update.message.reply_document(p)
        else:
            await update.message.reply_text("Wooops, some problem is here...")
                  
        if os.path.isdir(target_user):
            shutil.rmtree(target_user)
            
        if os.path.isfile(target_user + ".zip") :
            os.remove(target_user + ".zip")
        
def main(bot_tg_token, ig_username, ig_password) -> None:   
    ig_tools = InstagramTools(ig_username, ig_password)
    tg_tools = TelegramTools(bot_tg_token, ig_tools)

if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--token", help="Telegram bot token", required=True)
    argParser.add_argument("-u", "--username", help="Instagram username", required=True)
    argParser.add_argument("-p", "--password", help="Instagram password", required=True)
    args = argParser.parse_args()
    main(args.token, args.username, args.password)