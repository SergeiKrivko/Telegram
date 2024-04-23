from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQtUIkit.widgets import KitIconButton, KitHBoxLayout, KitLabel

from lib import tg


class VoicePlayer(KitHBoxLayout):
    def __init__(self, voice_message: tg.VoiceNote):
        super().__init__()
        self._voice = voice_message

        self.media_player = QMediaPlayer()
        self._audio = QAudioOutput()
        self.media_player.setAudioOutput(self._audio)
        if self._voice.voice.local.is_downloading_completed:
            self.media_player.setSource(QUrl.fromLocalFile(self._voice.voice.local.path))
        self.media_player.errorOccurred.connect(print)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        self.padding = 10
        self.spacing = 6

        self._button_play = KitIconButton('solid-play')
        self._button_play.setFixedSize(30, 30)
        self._button_play.clicked.connect(self.play)
        self.addWidget(self._button_play)

        self._button_pause = KitIconButton('solid-pause')
        self._button_pause.hide()
        self._button_pause.setFixedSize(30, 30)
        self._button_pause.clicked.connect(self.pause)
        self.addWidget(self._button_pause)

        self._duration_label = KitLabel(f"{voice_message.duration // 60:0>2}:{voice_message.duration % 60:0>2}")
        self.addWidget(self._duration_label)

    def play(self):
        if self._voice.voice.local.is_downloading_completed:
            self.media_player.play()
            self._button_pause.show()
            self._button_play.hide()
        else:
            tg.downloadFile(self._voice.voice.id, 1)

    def pause(self):
        self.media_player.pause()
        self._button_pause.hide()
        self._button_play.show()

    def on_downloaded(self, voice: tg.File):
        if self._voice.voice.id == voice.id:
            self._voice.voice = voice
            self.media_player.setSource(QUrl.fromLocalFile(self._voice.voice.local.path))
            self.media_player.play()
            self._button_pause.show()
            self._button_play.hide()

    def _on_media_status_changed(self, status):
        match status:
            case QMediaPlayer.MediaStatus.EndOfMedia:
                self._button_pause.hide()
                self._button_play.show()
