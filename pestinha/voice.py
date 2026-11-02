"""Chamada por voz offline, opcional, fora da thread de desenho do pet."""

import json
import queue
import threading
import time
from collections import deque
import re

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel

from .wakeword import WakeGate

MODEL_NAME = "vosk-model-small-en-us-0.15"


class VoiceListener(QObject):
    called = Signal()
    question = Signal(str)
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.model_path = root / "models" / MODEL_NAME
        self.question_model_path = root / "models" / "vosk-model-small-pt-0.3"
        self._stop = threading.Event()
        self._stop.set()
        self._thread = None
        self._model = None
        self._question_model = None
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
            if not self.question_model_path.is_dir():
                raise RuntimeError("Modelo de perguntas em português ausente. Execute setup/Preparar-Voz.py.")
            if self._question_model is None:
                self._question_model = Model(str(self.question_model_path))
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
            question_recognizer = KaldiRecognizer(self._question_model, rate)
            gate = WakeGate()
            recent = deque(maxlen=10)
            awaiting_question = False
            deadline = 0.0
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
                    if awaiting_question:
                        final = question_recognizer.AcceptWaveform(data)
                        if final:
                            text = json.loads(question_recognizer.Result()).get("text", "").strip()
                            text = re.sub(r"^(?:(?:oi|ei|olá|ola)\s+)?(?:nexus|néxus|néksus|nexos|nexo)\b[, ]*", "", text, flags=re.I).strip()
                            if len(text) >= 4:
                                if not stopped.is_set():
                                    self.question.emit(text)
                                awaiting_question = False
                        if time.monotonic() >= deadline:
                            awaiting_question = False
                        if not awaiting_question:
                            recognizer.Reset()
                            gate = WakeGate()
                            gate.last = time.monotonic()
                            recent.clear()
                            self._report("ouvindo")
                        continue
                    recent.append(data)
                    final = recognizer.AcceptWaveform(data)
                    result = json.loads(recognizer.Result() if final else recognizer.PartialResult())
                    text = result.get("text" if final else "partial", "")
                    if gate.accept(text, time.monotonic(), final=bool(final)) and not stopped.is_set():
                        question_recognizer.Reset()
                        for chunk in recent:
                            question_recognizer.AcceptWaveform(chunk)
                        awaiting_question = True
                        deadline = time.monotonic() + 15.0
                        self._report("ouvindo pergunta")
                        self.called.emit()
        except Exception as error:
            if not stopped.is_set():
                stopped.set()
                self.failed.emit(f"Não foi possível ouvir Nexus: {error}")
                self._report("indisponível")


class VoiceReply(QObject):
    """Respostas somente por escrito, em um balão ao lado do pet."""

    def __init__(self, pet, parent=None):
        super().__init__(parent)
        self.pet = pet
        self.bubble = QLabel("Oi! Estou aqui.")
        self.bubble.setTextFormat(Qt.PlainText)
        self.bubble.setWordWrap(True)
        self.bubble.setMaximumWidth(360)
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

    def _position(self):
        if not self.bubble.isVisible():
            return
        screen = self.pet.screen().availableGeometry()
        x = self.pet.frameGeometry().center().x() - self.bubble.width() // 2
        y = self.pet.frameGeometry().top() - self.bubble.height() - 10
        self.bubble.move(max(screen.left(), min(x, screen.right() - self.bubble.width())),
                         max(screen.top(), min(y, screen.bottom() - self.bubble.height())))

    def respond(self):
        self.show_text("Oi! Estou aqui.")

    def show_text(self, text, milliseconds=6000):
        self.bubble.setText(text)
        self.bubble.adjustSize()
        self.bubble.show()
        self._position()
        self.hide_timer.start(milliseconds)

    def stop(self):
        self.bubble.hide()
        self.hide_timer.stop()

    def close(self):
        self.stop()
        self.follow_timer.stop()
        self.bubble.close()
