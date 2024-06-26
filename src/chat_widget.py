from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QKeyEvent
from PyQtUIkit.widgets import *

from src.chat_bubble import TelegramChatBubble
from src.send_message_dialog import SendMessageDialog, MessageTypeMenu
from lib import tg
from src.telegram_manager import TgChat, TelegramManager


class TelegramChatWidget(KitVBoxLayout):
    loadRequested = pyqtSignal()
    sendMessageRequested = pyqtSignal(int)
    sendMessage = pyqtSignal(str)
    jumpRequested = pyqtSignal(object, object)

    def __init__(self, sm, manager: TelegramManager, chat: TgChat, thread=None, messages=None):
        super().__init__()
        self._sm = sm

        self._bubbles = []

        self.spacing = 6

        self._scroll_area = _ScrollArea()
        self._scroll_area.loadRequested.connect(self.loadRequested.emit)
        self.addWidget(self._scroll_area, 1)

        self._scroll_layout = _ScrollWidget()
        self._scroll_layout.spacing = 6
        self._scroll_layout.padding = 10
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll_area.setWidget(self._scroll_layout)

        bottom_layout = KitHBoxLayout()
        self.addWidget(bottom_layout)

        self._button_document = KitIconButton('solid-document')
        self._button_document.setFixedSize(30, 30)
        self._button_document.clicked.connect(self._run_menu)
        # self._button_document.setMenu(self.menu)
        bottom_layout.addWidget(self._button_document)

        self._text_edit = ChatInputArea()
        self._text_edit.returnPressed.connect(self.send_message)
        bottom_layout.addWidget(self._text_edit, 1)

        self._button = KitIconButton('solid-paper-plane')
        self._button.setFixedSize(30, 30)
        self._button.clicked.connect(self.send_message)
        bottom_layout.addWidget(self._button)

        self._last_pos = 0
        self._last_max = 0

        self._chat = chat
        self._thread = thread
        self._manager = manager
        self.loading = False

        self._scroll_bar = self._scroll_area.verticalScrollBar()
        self._scroll_bar.valueChanged.connect(self._on_scroll_bar_value_changed)

        self._messages_to_load = 10
        self.loadRequested.connect(self.add_messages_to_load)

        if not self._chat.permissions.can_send_basic_messages:
            self._text_edit.hide()
            self._button.hide()
            self._button_document.hide()

        self.sendMessageRequested.connect(self._sending_document)
        self._manager.deleteMessages.connect(self._delete_messages)

        if messages:
            self.loading = True
            for el in messages:
                self.add_message(el)

    def show(self) -> None:
        if self.isHidden():
            # self._scroll_bar.setValue(self._scroll_bar.maximum())
            self.check_if_need_to_load()
        super().show()

    def _delete_messages(self, chat_id, message_ids):
        if chat_id == self._chat.id:
            self._delete_bubbles(message_ids)

    def _sending_document(self, doc_type):
        dialog = SendMessageDialog(self, self._sm, self._chat, self._text_edit.toPlainText(), doc_type)
        dialog.exec()

    def check_if_need_to_load(self):
        if self.loading:
            return
        if len(self._bubbles) < self._messages_to_load:
            first_message = None if self._chat.first_message is None else self._chat.first_message.id
            if isinstance(self._chat.type, tg.ChatTypeSupergroup) and self._chat.type.is_channel and self._thread:
                tg.getMessageThreadHistory(self._chat.id, self._thread, from_message_id=first_message, limit=10)
            else:
                tg.getChatHistory(self._chat.id, from_message_id=first_message, limit=10)
            self.loading = True

    def _on_scroll_bar_value_changed(self):
        el = None
        for el in self._bubbles:
            if not (0 < el.y() - self._scroll_bar.value() + el.height() < self.height()):
                break
        if el is not None:
            el.set_read()

    def add_messages_to_load(self):
        self._messages_to_load = self._chat.message_count() + 10
        self.check_if_need_to_load()

    def add_message(self, message: tg.Message):
        self.add_bubble(message)

    def insert_message(self, message: tg.Message):
        self.insert_bubble(message)

    def insert_bubble(self, message: tg.Message):
        bubble = TelegramChatBubble(message, self._manager)
        bubble.jumpRequested.connect(self.jumpRequested.emit)
        bubble.set_max_width(int(self.width() * 0.8))
        if isinstance(self._chat.type, tg.ChatTypePrivate):
            bubble.hide_sender()
        self._insert_bubble(bubble)

    def add_bubble(self, message: tg.Message, *args):
        bubble = TelegramChatBubble(message, self._manager)
        bubble.jumpRequested.connect(self.jumpRequested.emit)
        bubble.set_max_width(int(self.width() * 0.8))
        if isinstance(self._chat.type, tg.ChatTypePrivate):
            bubble.hide_sender()
        self._add_buble(bubble)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        for el in self._bubbles:
            el.set_max_width(min(1000, int(self.width() * 0.8)))

    def send_message(self):
        if not (text := self._text_edit.toPlainText()):
            return
        # self.sendMessage.emit(text)
        tg.sendMessage(self._chat.id, input_message_content=tg.InputMessageText(text=tg.FormattedText(text=text)))
        self._text_edit.setText("")

    def _run_menu(self):
        menu = MessageTypeMenu(self)
        menu.move(self.mapToGlobal(self._button_document.pos()) - QPoint(0, 100))
        menu.exec()
        if menu.selected_type:
            self.sendMessageRequested.emit(menu.selected_type)

    def _add_buble(self, bubble):
        self._scroll_layout.addWidget(bubble)
        self._bubbles.append(bubble)

    def _insert_bubble(self, bubble):
        self._scroll_layout.insertWidget(0, bubble)
        self._bubbles.insert(0, bubble)

    def _delete_bubbles(self, message_ids):
        message_ids = set(message_ids)
        i = 0
        while i < len(self._bubbles):
            if self._bubbles[i]._message.id in message_ids:
                self._bubbles[i].setParent(None)
                self._bubbles.pop(i)

            i += 1


class ChatInputArea(KitTextEdit):
    returnPressed = pyqtSignal()
    resize = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self):
        height = self.verticalScrollBar().maximum()
        if not height:
            self.setFixedHeight(30)
            height = self.verticalScrollBar().maximum()
        self.setFixedHeight(min(300, self.height() + height))

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter:
            self.returnPressed.emit()
        else:
            super().keyPressEvent(e)


class _ScrollArea(KitScrollArea):
    loadRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._last_pos = 0
        self._last_max = 0
        self.verticalScrollBar().valueChanged.connect(self._on_scrolled)

    def setWidget(self, w: '_ScrollWidget') -> None:
        super().setWidget(w)
        w.resized.connect(self._on_resized)

    def _on_scrolled(self, pos):
        if pos < 50:
            self.loadRequested.emit()

    def _on_resized(self) -> None:
        self._last_pos = self.verticalScrollBar().value()
        if self._last_pos > self._last_max - 30:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        # elif self._last_pos < 50:
        else:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum() -
                                              self._last_max + self._last_pos)

        self._last_max = self.verticalScrollBar().maximum()


class _ScrollWidget(KitVBoxLayout):
    resized = pyqtSignal()

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.resized.emit()
