import datetime

from PyQt6.QtCore import pyqtSignal, Qt
from PyQtUIkit.widgets import *

from src import config
from src.chat_list_widget import TelegramListWidget
from src.chat_widget import TelegramChatWidget
from src.send_message_dialog import SendMessageDialog
from lib import tg
from src.settings_manager import SettingsManager
from src.telegram_manager import TelegramManager, TgChat


class TelegramWidget(KitMainWindow):
    def __init__(self):
        super().__init__()
        self.spacing = 6
        self._sm = SettingsManager()
        self.set_theme('Dark')
        self.resize(480, 640)

        main_layout = KitHBoxLayout()
        main_layout.padding = 10
        main_layout.spacing = 6
        self.setCentralWidget(main_layout)

        self._manager = TelegramManager(self._sm)
        self._manager.chatsLoaded.connect(self.update_chats)
        self._manager.addMessage.connect(self.add_message)
        self._manager.insertMessage.connect(self.insert_message)
        self._manager.loadingFinished.connect(self.loading_finished)
        self._manager.threadLoaded.connect(self._jump)
        self._manager.authorization.connect(self.get_authentication_data)
        self._manager.updateFolders.connect(self.update_folders)

        list_layout = KitVBoxLayout()
        main_layout.addWidget(list_layout)

        self._tab_bar = KitTabBar()
        self._tab_bar.setFixedHeight(26)
        self._tab_bar.currentChanged.connect(self._on_folder_selected)
        list_layout.addWidget(self._tab_bar)

        self._list_widget = TelegramListWidget(self._manager)
        self._list_widget.currentItemChanged.connect(self.show_chat)
        list_layout.addWidget(self._list_widget)

        self._chats_layout = KitVBoxLayout()
        self._chats_layout.setSpacing(0)
        self._chats_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._chats_layout)

        self._top_panel = TelegramTopWidget(self._manager)
        self._top_panel.hide()
        self._top_panel.buttonBackPressed.connect(self.hide_chat)
        self._chats_layout.addWidget(self._top_panel)

        self._chat_widgets = dict()
        self._current_chat = None
        self._last_chats = []

        self._manager_started = False
        self._folders = []
        # self._manager.start()

    def command(self, text, file=None, image=None, *args, **kwargs):
        dialog = SelectChatDialog(self, self._manager)
        if dialog.exec():
            chat = self._manager.get_chat(dialog.chat)
            dialog2 = SendMessageDialog(chat, text, SendMessageDialog.TEXT_ONLY)
            if dialog2.exec():
                tg.sendMessage(dialog.chat, input_message_content=tg.InputMessageText(
                    text=tg.FormattedText(text=dialog2.text_area.toPlainText())))

    def show(self):
        if not self._manager_started:
            self._manager.start()
            self._manager_started = True
        super().show()

    def update_folders(self, folders):
        self._folders = list(folders.values())
        for key in folders:
            self._tab_bar.addTab(key)

    def update_chats(self, chat_ids):
        self._list_widget.clear()
        for el in chat_ids:
            self.add_chat(self._manager.get_chat(el))

    def _on_folder_selected(self):
        tg.getChats(self._folders[self._tab_bar.currentIndex()], 100)

    def add_message(self, message: tg.Message):
        if (message.chat_id, message.message_thread_id) not in self._chat_widgets:
            return
        chat = self._manager.get_chat(message.chat_id)
        if isinstance(chat.type, tg.ChatTypeSupergroup) and not chat.type.is_channel:
            thread = 0
        else:
            thread = message.message_thread_id
        self._chat_widgets[(message.chat_id, message.message_thread_id)].add_message(message)

    def insert_message(self, message: tg.Message):
        chat = self._manager.get_chat(message.chat_id)
        if isinstance(chat.type, tg.ChatTypeSupergroup) and not chat.type.is_channel:
            thread = 0
        else:
            thread = message.message_thread_id
        self._chat_widgets[(message.chat_id, thread)].insert_message(message)

    def loading_finished(self, chat: TgChat, thread=0):
        if isinstance(chat.type, tg.ChatTypeSupergroup) and not chat.type.is_channel:
            thread = 0
        self._chat_widgets[(chat.id, thread)].loading = False
        self._chat_widgets[(chat.id, thread)].check_if_need_to_load()

    def add_chat(self, chat, thread=0, messages=None):
        if thread == 0:
            self._list_widget.add_item(chat)
        if (chat.id, thread) in self._chat_widgets:
            return

        chat_widget = TelegramChatWidget(self._sm, self._manager, chat, thread)
        chat_widget.hide()
        chat_widget.jumpRequested.connect(self._jump)
        self._chat_widgets[(chat.id, thread)] = chat_widget
        self._chats_layout.addWidget(chat_widget)

    def _jump(self, thread_info: tg.MessageThreadInfo):
        self.add_chat(self._manager.get_chat(thread_info.chat_id), thread_info.message_thread_id,
                      messages=thread_info.messages)
        self.show_chat(thread_info.chat_id, thread_info.message_thread_id)

    def show_chat(self, chat_id, thread=0):
        if isinstance(chat_id, str):
            chat_id = int(chat_id)
        if chat_id is None:
            self.hide_chat()
            return
        if (chat_id, thread) not in self._chat_widgets:
            return
        if self._current_chat in self._chat_widgets:
            if len(self._last_chats) > 1 and (chat_id, thread) == self._last_chats[-1]:
                self._last_chats.pop(-1)
            else:
                self._last_chats.append(self._current_chat)
            self._chat_widgets[self._current_chat].hide()
        self._list_widget.hide()
        self._tab_bar.hide()
        self._top_panel.show()
        self._top_panel.set_chat(self._manager.get_chat(chat_id))
        self._chat_widgets[(chat_id, thread)].show()
        self._current_chat = (chat_id, thread)
        tg.openChat(chat_id)
        # self._manager.get_messages(chat_id)

    def hide_chat(self):
        if self._current_chat in self._chat_widgets:
            self._chat_widgets[self._current_chat].hide()
        self._current_chat = None
        if self._last_chats:
            self.show_chat(*self._last_chats.pop(-1))
        else:
            self._list_widget.show()
            self._tab_bar.show()
            self._top_panel.hide()
            self._list_widget.set_current_id(None)

    def get_authentication_data(self, state):
        dialog = PasswordWidget(self, state)
        if dialog.exec():
            self._manager.authenticate_user(dialog.get_str1(), dialog.get_str2())

    def finish_work(self):
        self._manager.terminate()


class TelegramTopWidget(KitHBoxLayout):
    buttonBackPressed = pyqtSignal()

    def __init__(self, manager: TelegramManager):
        super().__init__()
        self._manager = manager
        self._chat = None

        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.padding = 3
        self.spacing = 6

        self._button_back = KitIconButton('line-arrow-back')
        self._button_back.size = 36
        self._button_back.clicked.connect(self.buttonBackPressed.emit)
        self.addWidget(self._button_back)

        labels_layout = KitVBoxLayout()
        self.addWidget(labels_layout)

        self._name_label = KitLabel()
        labels_layout.addWidget(self._name_label)

        self._status_label = KitLabel()
        labels_layout.addWidget(self._status_label)

        self._manager.updateUserStatus.connect(self._on_user_status_updated)

    def set_chat(self, chat: TgChat):
        self._chat = chat
        self._name_label.setText(chat.title)
        if isinstance(chat.type, tg.ChatTypePrivate):
            self._status_label.show()
            user = self._manager.get_user(chat.type.user_id)
            if isinstance(user.status, tg.UserStatusOnline):
                self._status_label.setText("В сети")
            else:
                self._status_label.setText(f"Был(а) в {self.get_time(user.status.was_online)}")
        else:
            self._status_label.hide()

    @staticmethod
    def get_time(t: int):
        return datetime.datetime.fromtimestamp(t).strftime("%H:%M")

    def _on_user_status_updated(self, user_id: str | int):
        if not isinstance(self._chat, TgChat):
            return
        user_id = int(user_id)
        if isinstance(self._chat.type, tg.ChatTypePrivate):
            self._status_label.show()
            user = self._manager.get_user(self._chat.type.user_id)
            if isinstance(user.status, tg.UserStatusOnline):
                self._status_label.setText("В сети")
            else:
                self._status_label.setText(f"Был(а) в {self.get_time(user.status.was_online)}")


class PasswordWidget(KitDialog):
    def __init__(self, parent, state):
        super().__init__(parent)
        self.name = config.APP_NAME

        self.setFixedWidth(300)

        if isinstance(state, tg.AuthorizationStateWaitPhoneNumber):
            self._text = "Пожалуйста, введите свой номер телефона:"
            self._password_mode = False
            self._2_lines = False
        elif isinstance(state, tg.AuthorizationStateWaitCode):
            self._text = "Пожалуйста, введите полученный вами код аутентификации:"
            self._password_mode = True
            self._2_lines = False
        elif isinstance(state, tg.AuthorizationStateWaitEmailAddress):
            self._text = "Пожалуйста, введите свой адрес электронной почты:"
            self._password_mode = False
            self._2_lines = False
        elif isinstance(state, tg.AuthorizationStateWaitEmailCode):
            self._text = "Пожалуйста, введите полученный вами по электронной почте код аутентификации:"
            self._password_mode = True
            self._2_lines = False
        elif isinstance(state, tg.AuthorizationStateWaitRegistration):
            self._text = "Пожалуйста, введите имя и фамилию:"
            self._password_mode = True
            self._2_lines = True
        elif isinstance(state, tg.AuthorizationStateWaitPassword):
            self._text = "Пожалуйста, введите свой пароль:"
            self._password_mode = True
            self._2_lines = False

        layout = KitVBoxLayout()
        layout.padding = 10
        layout.spacing = 6
        self.setWidget(layout)

        self._label = KitLabel(self._text)
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        self._line_edit = KitLineEdit()
        if self._password_mode:
            self._line_edit.setEchoMode(KitLineEdit.EchoMode.Password)
        self._line_edit.returnPressed.connect(self.accept)
        layout.addWidget(self._line_edit)

        self._line_edit2 = KitLineEdit()
        if self._password_mode:
            self._line_edit2.setEchoMode(KitLineEdit.EchoMode.Password)
        self._line_edit2.returnPressed.connect(self.accept)
        if not self._2_lines:
            self._line_edit2.hide()
        layout.addWidget(self._line_edit2)

        buttons_layout = KitHBoxLayout()
        layout.addWidget(buttons_layout)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        buttons_layout.spacing = 6

        self._button = KitButton("OK")
        self._button.setFixedSize(80, 24)
        self._button.clicked.connect(self.accept)
        buttons_layout.addWidget(self._button)

    def get_str1(self):
        return self._line_edit.text

    def get_str2(self):
        return self._line_edit2.text


class SelectChatDialog(KitDialog):
    def __init__(self, parent, manager: TelegramManager):
        super().__init__(parent)
        self.name = "Выберите чат"
        self._manager = manager
        self.chat = None

        layout = KitVBoxLayout()
        self.setWidget(layout)

        self._list_widget = TelegramListWidget(manager)
        self._list_widget.currentItemChanged.connect(self._on_chat_selected)
        layout.addWidget(self._list_widget)

        for el in self._manager._chats.values():
            self._list_widget.add_item(el)

    def _on_chat_selected(self, chat_id):
        chat_id = int(chat_id)
        self.chat = chat_id
        self.accept()
