from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from PyQtUIkit.core import KitFont
from PyQtUIkit.widgets import *

from lib import tg
from src.telegram_manager import TelegramManager, TgChat


class TelegramListWidget(KitScrollArea):
    currentItemChanged = pyqtSignal(str)

    def __init__(self, manager: TelegramManager):
        super().__init__()
        self._manager = manager

        self._layout = KitVBoxLayout()
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._layout)

        self._items = dict()

    def clear(self):
        for el in self._items.values():
            el.setParent(None)
            el.disabled = True
            el.hide()
        self._items.clear()

    def _on_chat_updated(self, chat_id):
        for el in self._items.values():
            el.update_chat(chat_id)

    def _on_item_selected(self, chat_id):
        if isinstance(chat_id, str):
            chat_id = int(chat_id)
        for key, item in self._items.items():
            if key != chat_id:
                item.set_selected(False)
        self.currentItemChanged.emit(str(chat_id))

    def set_current_id(self, chat_id):
        for key, item in self._items.items():
            if key != chat_id:
                item.set_selected(False)
        if chat_id in self._items:
            self._items[chat_id].set_selected(True)

    def add_item(self, chat: TgChat):
        item = TelegramListWidgetItem(self._tm, chat, self._manager)
        item.selected.connect(self._on_item_selected)
        chat_id = chat.id
        self._items[chat_id] = item
        self._layout.addWidget(item)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        self._set_items_width()

    def _set_items_width(self):
        width = self.width() - 19
        for el in self._items.values():
            el.setFixedWidth(width)


class TelegramListWidgetItem(KitLayoutButton):
    selected = pyqtSignal(str)

    def __init__(self, tm, chat: TgChat, manager: TelegramManager):
        super().__init__()
        self._tm = tm
        self._chat = chat
        self._chat_id = chat.id
        self._selected = False
        self._hover = False
        self._manager = manager
        self.disabled = False

        self.setFixedHeight(54)

        self.padding = 2
        self.spacing = 6
        self.border = 0
        self.radius = 0
        self.setCheckable(True)
        self.on_click = self.set_selected

        self._icon_label = KitLabel()
        self._icon_label.setFixedWidth(50)

        self._photo = None
        if chat.photo is not None:
            self._photo = chat.photo.small
            if self._photo.local.can_be_downloaded:
                tg.downloadFile(self._photo.id, 1)
            manager.updateFile.connect(self.update_icon)
            if self._photo.local.is_downloading_completed:
                self._icon_label.setPixmap(QPixmap(self._photo.local.path).scaled(48, 48))
        else:
            self._icon_label.setText(self._chat.title[0])
            self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._icon_label.font_size = KitFont.Size.BIG
        self.addWidget(self._icon_label)

        self._name_label = KitLabel(self._chat.title)
        self.addWidget(self._name_label)

        last_message_layout = KitHBoxLayout()
        last_message_layout.padding = 0
        last_message_layout.spacing = 6
        self.addWidget(last_message_layout)

        self._last_message_label = LastMessageWidget(self._tm, self._manager)
        self.update_last_message(self._chat.last_message)
        last_message_layout.addWidget(self._last_message_label, 10)

        self._unread_count_label = KitLabel(str(self._chat.unread_count))
        self._unread_count_label.setMinimumWidth(30)
        self._unread_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        last_message_layout.addWidget(self._unread_count_label, 1)
        if self._chat.unread_count == 0:
            self._unread_count_label.hide()

    def update_last_message(self, message):
        if message is not None and (isinstance(self._chat.type, tg.ChatTypeBasicGroup) or
                                    isinstance(self._chat.type, tg.ChatTypeSupergroup) and hasattr(
                    message.sender_id, 'user_id')):
            sender = self._manager.get_user(message.sender_id.user_id)
        else:
            sender = None
        self._last_message_label.open_message(message, sender)

    def update_chat(self, chat_id: str):
        if int(chat_id) != self._chat.id or self.disabled:
            return
        message = self._chat.last_message
        if isinstance(message, tg.Message):
            self.update_last_message(message)

        self._unread_count_label.setText(str(self._chat.unread_count))
        if self._chat.unread_count == 0:
            self._unread_count_label.hide()
        else:
            self._unread_count_label.show()

    def update_icon(self, image: tg.File):
        if isinstance(self._photo, tg.File) and image.id == self._photo.id and \
                self._photo.local.is_downloading_completed:
            self._icon_label.setPixmap(QPixmap(self._photo.local.path).scaled(44, 44))

    def set_selected(self, status):
        if self._selected == bool(status):
            return
        self._selected = bool(status)
        if status:
            self.selected.emit(str(self._chat_id))


class LastMessageWidget(KitHBoxLayout):
    def __init__(self, tm, manager):
        super().__init__()
        self._tm = tm
        self._manager = manager

        self.spacing = 6
        self.setMinimumWidth(0)

        self._icon_label = KitLabel()
        self._icon_label.hide()
        self._icon_label.setFixedSize(20, 20)
        self.addWidget(self._icon_label)

        v_layout = KitVBoxLayout()
        v_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        v_layout.setSpacing(1)
        self.addWidget(v_layout)

        # self._sender_label = Label()
        # self._sender_label.setWordWrap(True)
        # self._sender_label.setFixedHeight(12)
        # self._sender_label.mouseMoving.connect(self.mouseMoving.emit)
        # v_layout.addWidget(self._sender_label)

        self._text_label = KitLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setFixedHeight(26)
        v_layout.addWidget(self._text_label)

    def set_theme(self):
        self._text_label.setFont(self._tm.font_small)
        # self._sender_label.setFont(self._tm.font_small)
        # self._sender_label.setStyleSheet(f"color: {self._tm['TestPassed'].name()}")

    def open_message(self, message: tg.Message, sender: tg.User = None):
        text = ""
        icon = None

        if sender:
            text += sender.first_name + ': '

        if message is not None:
            if isinstance(message.content, tg.MessageText):
                text += message.content.text.text
            if isinstance(message.content, tg.MessagePhoto):
                icon = message.content.photo.minithumbnail
                if message.content.caption.text:
                    text += message.content.caption.text
                else:
                    text += "Фотография"
            if isinstance(message.content, tg.MessageDocument):
                if message.content.caption.text:
                    text += message.content.caption.text
                else:
                    text += message.content.document.file_name

        self._text_label.setText(text[:80])
        if isinstance(icon, tg.Minithumbnail):
            self._icon_label.show()
            self._icon_label.setPixmap(QPixmap(self._manager.load_minithumbnail(icon)))
        else:
            self._icon_label.hide()
