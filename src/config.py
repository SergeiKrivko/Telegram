from distutils.command.config import config

APP_NAME = "Telegram"
APP_VERSION = "1.0.0"
ORGANISATION_NAME = "SergeiKrivko"

try:
    from secret_config import *
except ImportError:
    TELEGRAM_API_KEY = 1234567890
    TELEGRAM_API_HASH = '<API_KEY>'
