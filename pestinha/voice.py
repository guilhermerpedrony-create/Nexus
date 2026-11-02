"""Chamada por voz offline, opcional, fora da thread de desenho do pet."""

import json
import queue
import threading
import time

from PySide6.QtCore import QObject, QLocale, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QLabel

from .wakeword import WakeGate

MODEL_NAME = "vosk-model-small-en-us-0.15"


class VoiceListener(QObject):
    called = Signal()
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.model_path = root / "models" / MODEL_NAME
        self._stop = threading.Event()
        self._stop.set()
        self._thread = None
        self._model = None
        self._enabled = False
        self._status = None

    def _report(self, status):
        if self._status != status:
            self._status = status
            self.status.emit(status)

    @property
    def active(self):
        return not self._stop.is_set()

    def start(self):
        if self._enabled:
            return
        # A thread anterior fecha o dispositivo antes de uma nova abertura.
        if self._thread is not None and self._thread.is_alive():
            return
        self._enabled = True
        self._stop = threading.Event()
        self._report("carregando")
        self._thread = threading.Thread(target=self._listen, args=(self._stop,), daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False
        self._stop.set()
        self._report("desligado")

    def close(self):
        self.stop()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _listen(self, stopped):
        try:
            if not self.model_path.is_dir():
                raise RuntimeError("Modelo de voz ausente. Execute setup/Preparar-Voz.py antes de ligar o microfone.")
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel

            SetLogLevel(-1)
            if self._model is None:
                self._model = Model(str(self.model_path))
            if stopped.is_set():
                return
            rate = int(sd.query_devices(kind="input")["default_samplerate"])
            audio = queue.Queue(maxsize=12)

            def receive(data, _frames, _time_info, _status):
                if not stopped.is_set():
                    try:
                        audio.put_nowait(bytes(data))
                    except queue.Full:
                        pass  # descarta excesso; nunca deixa a fila crescer sem limite

            # Modelo inglês inclui o nome Nexus. [unk] evita forçar toda fala a virar o nome.
            recognizer = KaldiRecognizer(self._model, rate, json.dumps(["nexus", "[unk]"]))
            gate = WakeGate()
            with sd.RawInputStream(samplerate=rate, blocksize=max(1, rate // 5),
                                   channels=1, dtype="int16", callback=receive):
                if stopped.is_set():
                    return
                self._report("ouvindo")
                while not stopped.is_set():
                    try:
                        data = audio.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    final = recognizer.AcceptWaveform(data)
                    result = json.loads(recognizer.Result() if final else recognizer.PartialResult())
                    text = result.get("text" if final else "partial", "")
                    if gate.accept(text, time.monotonic(), final=bool(final)) and not stopped.is_set():
                        self.called.emit()
        except Exception as error:
            if not stopped.is_set():
                stopped.set()
                self.failed.emit(f"Não foi possível ouvir Nexus: {error}")
                self._report("indisponível")


class VoiceReply(QObject):
    """Resposta curta em balão e pela voz instalada no sistema, sem serviço de chat."""

    def __init__(self, pet, parent=None):
        super().__init__(parent)
        self.pet = pet
        self.bubble = QLabel("Oi! Estou aqui.")
        self.bubble.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                                   | Qt.WindowDoesNotAcceptFocus)
        self.bubble.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.bubble.setStyleSheet("QLabel { background: #10251b; color: #dfffe6; border: 1px solid #63e56f; "
                                  "border-radius: 12px; padding: 12px 18px; font: 14px 'Segoe UI'; }")
        self.bubble.adjustSize()
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.bubble.hide)
        self.follow_timer = QTimer(self)
        self.follow_timer.setInterval(50)
        self.follow_timer.timeout.connect(self._position)
        self.follow_timer.start()
        self.speaker = None
        self._speech_tried = False

    def _position(self):
        if not self.bubble.isVisible():
            return
        screen = self.pet.screen().availableGeometry()
        x = self.pet.frameGeometry().center().x() - self.bubble.width() // 2
        y = self.pet.frameGeometry().top() - self.bubble.height() - 10
        self.bubble.move(max(screen.left(), min(x, screen.right() - self.bubble.width())),
                         max(screen.top(), min(y, screen.bottom() - self.bubble.height())))

    def respond(self, aloud=True):
        self.bubble.show()
        self._position()
        self.hide_timer.start(4000)
        if aloud:
            if not self._speech_tried:
                self._speech_tried = True
                try:
                    from PySide6.QtTextToSpeech import QTextToSpeech
                    self.speaker = QTextToSpeech(self)
                    self.speaker.setLocale(QLocale("pt_BR"))
                except (ImportError, RuntimeError):
                    self.speaker = None
            if self.speaker is not None:
                self.speaker.say("Oi! Estou aqui.")
            else:
                QApplication.beep()

    def stop(self):
        self.bubble.hide()
        self.hide_timer.stop()
        if self.speaker is not None:
            self.speaker.stop()

    def close(self):
        self.stop()
        self.follow_timer.stop()
        self.bubble.close()
