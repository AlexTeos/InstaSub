import configparser
from pathlib import Path
from instagramtools import InstagramTools
from telegramtools import TelegramTools


def main(bot_tg_token, ig_username, ig_password) -> None:
    ig_tools = InstagramTools(ig_username, ig_password)
    TelegramTools(bot_tg_token, ig_tools)


if __name__ == "__main__":
    config_file = Path('/ext/instasub.ini')
    if not config_file.is_file():
        config = configparser.ConfigParser()
        config['telegram'] = {'token': ''}
        config['instagram'] = {'username': '',
                               'password': ''}
        with open(config_file, 'w+') as configfile:
            config.write(configfile)

        print('Config file created:', config_file)
    else:
        config = configparser.ConfigParser()
        config.read(config_file)
        if 'telegram' in config and 'instagram' in config and 'token' in config['telegram'] and 'username' in \
                config['instagram'] and 'password' in config['instagram'] and config['telegram']['token'] != '' and \
                config['instagram']['username'] != '' and config['instagram']['password'] != '':
            main(config['telegram']['token'], config['instagram']['username'], config['instagram']['password'])
        else:
            print('Config file is incorrect:', config_file.name)
