import argparse
from instagramtools import InstagramTools
from telegramtools import TelegramTools


def main(bot_tg_token, ig_username, ig_password) -> None:
    ig_tools = InstagramTools(ig_username, ig_password)
    TelegramTools(bot_tg_token, ig_tools)


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument(
        "-t", "--token", help="Telegram bot token", required=True)
    argParser.add_argument(
        "-u", "--username", help="Instagram username", required=True)
    argParser.add_argument(
        "-p", "--password", help="Instagram password", required=True)
    args = argParser.parse_args()
    main(args.token, args.username, args.password)
