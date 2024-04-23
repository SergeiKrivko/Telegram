import sys

from PyQtUIkit.widgets import KitApplication

from src import config
from src.telegram_widget import TelegramWidget


def main():
    app = KitApplication(TelegramWidget)
    app.setOrganizationName(config.ORGANISATION_NAME)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
