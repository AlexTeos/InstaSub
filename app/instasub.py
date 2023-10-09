import configparser
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from instagramtools import InstagramTools
from telegramtools import TelegramTools


def main(bot_tg_token, tg_admin_id, ig_username, ig_password) -> None:
    ig_tools = InstagramTools(ig_username, ig_password)
    TelegramTools(bot_tg_token, tg_admin_id, ig_tools)


def setup_logger():
    log_file = '/ext/instasub.log'
    log_formatter = logging.Formatter('%(asctime)s [%(process)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')

    is_rotating_handler = RotatingFileHandler(log_file, maxBytes=64 * 1024 * 1024, mode='a', backupCount=1)
    is_rotating_handler.setFormatter(log_formatter)
    is_rotating_handler.setLevel(logging.INFO)

    root_rotating_handler = RotatingFileHandler(log_file, maxBytes=64 * 1024 * 1024, mode='a', backupCount=1)
    root_rotating_handler.setFormatter(log_formatter)
    root_rotating_handler.setLevel(logging.WARNING)

    logging.getLogger('root').setLevel(logging.WARNING)
    logging.getLogger('root').addHandler(root_rotating_handler)

    logging.getLogger('instasub').setLevel(logging.INFO)
    logging.getLogger('instasub').addHandler(is_rotating_handler)


if __name__ == "__main__":
    setup_logger()
    logger = logging.getLogger("instasub")
    try:
        config_file = Path('/ext/instasub.ini')
        if not config_file.is_file():
            config = configparser.ConfigParser()
            config['telegram'] = {'token': ''}
            config['instagram'] = {'username': '',
                                   'password': ''}
            with open(config_file, 'w+') as configfile:
                config.write(configfile)

            logger.info('Config file created:', config_file)
        else:
            config = configparser.ConfigParser()
            config.read(config_file)
            if 'telegram' in config and 'instagram' in config and 'token' in config['telegram'] and 'admin' in config[
                'telegram'] and 'username' in config['instagram'] and 'password' in config['instagram'] and \
                    config['telegram']['token'] != '' and config['telegram']['admin'] != '' and config['instagram'][
                'username'] != '' and config['instagram']['password'] != '':
                logger.info('Start bot with arguments: TGToken - {0} TGAdmin - {1} IGUser - {2} IGPass - {3} '.format(
                    config['telegram']['token'], config['telegram']['admin'], config['instagram']['username'],
                    config['instagram']['password']))
                main(config['telegram']['token'], config['telegram']['admin'], config['instagram']['username'],
                     config['instagram']['password'])
            else:
                logger.warning('Config file is incorrect:' + config_file.name)
    except Exception as e:
        logger.critical("Unhandled exception occurred: " + str(e))
