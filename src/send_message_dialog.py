from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileDialog
from PyQtUIkit.widgets import *

from lib import tg

from src.settings_manager import SettingsManager


class SendMessageDialog(KitDialog):
    TEXT_ONLY = 0
    FILE = 1
    IMAGE = 2
    PROJECT = 3
    VIDEO = 4

    def __init__(self, parent, sm: SettingsManager, chat: tg.Chat, text='', option=0):
        super().__init__(parent)
        self.name = "Отправка сообщения"
        self._sm = sm
        self._chat = chat
        self._option = option

        self.setFixedSize(400, 300)

        layout = KitVBoxLayout()
        layout.spacing = 6
        self.setWidget(layout)

        self._chat_label = KitLabel(chat.title)
        layout.addWidget(self._chat_label)

        match self._option:
            case SendMessageDialog.FILE:
                path, _ = QFileDialog.getOpenFileName(caption="Выберите файл для отправки")
                if not path:
                    self.reject()
                    return
                self.specific_widget = KitLineEdit()
                self.specific_widget.setText(path)
                self.specific_widget.setReadOnly(True)
                layout.addWidget(self.specific_widget)

        self.text_area = KitTextEdit()
        self.text_area.setText(text)
        layout.addWidget(self.text_area)

        buttons_layout = KitHBoxLayout()
        buttons_layout.spacing = 6
        layout.addWidget(buttons_layout)

        self._button_cancel = KitButton("Отмена")
        self._button_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self._button_cancel)

        self._button_add = KitButton("Добавить")
        self._button_add.clicked.connect(self.reject)
        buttons_layout.addWidget(self._button_add)
        self._button_add.hide()

        self._button_send = KitButton("Отправить")
        # self._button_send.clicked.connect(self.accept)
        self._button_send.clicked.connect(self._send)
        buttons_layout.addWidget(self._button_send)

    def _send(self):
        match self._option:
            case SendMessageDialog.FILE:
                tg.sendMessage(self._chat.id, input_message_content=tg.InputMessageDocument(
                    document=tg.InputFileLocal(path=self.specific_widget.text()),
                    caption=tg.FormattedText(text=self.text_area.toPlainText())))
        self.accept()


class MessageTypeMenu(KitMenu):
    def __init__(self, parent):
        super().__init__(parent)
        self.selected_type = 0

        action = self.addAction("Файл", 'solid-document')
        action.triggered.connect(lambda: self.set_type(SendMessageDialog.FILE))

        action = self.addAction("Изображение", 'solid-image')
        action.triggered.connect(lambda: self.set_type(SendMessageDialog.IMAGE))

        # action = self.addAction(QIcon(self._tm.get_image('icons/projects')), "Текущий проект")
        # action.triggered.connect(lambda: self.set_type(SendMessageDialog.PROJECT))

    def set_type(self, t):
        self.selected_type = t
