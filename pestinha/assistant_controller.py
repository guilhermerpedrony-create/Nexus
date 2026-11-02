"""Liga conversa e ações à interface, sem bloquear a animação do pet."""

from datetime import datetime
import threading
import uuid

from PySide6.QtCore import QObject, Signal

from .assistant import LocalChat, open_application, requested_task
from .ui.chat import ChatWindow


class AssistantController(QObject):
    answered = Signal(str)
    failed = Signal(str)

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.client = LocalChat(app.paths.root)
        self.window = ChatWindow()
        self.window.submitted.connect(self.ask)
        self.answered.connect(self._answer)
        self.failed.connect(self._error)
        self.pending = False
        self.closed = False

    def open(self):
        self.window.show()
        self.window.raise_()
        self.window.input.setFocus()

    def ask(self, text):
        text = text.strip()[:4000]
        if not text or self.closed:
            return
        if self.app._congelado():
            return
        if self.pending:
            self.app.voice_reply.show_text("Um instante, estou terminando a resposta anterior.")
            return
        self.window.show()
        self.window.append("Você", text)
        task = requested_task(text)
        if task:
            try:
                answer = self._perform(task)
            except (OSError, RuntimeError, ValueError):
                self._error("Não consegui concluir esse pedido. Tente novamente.")
            else:
                self.client.history = [*self.client.history[-10:], {"role": "user", "content": text},
                                       {"role": "assistant", "content": answer}]
                self._answer(answer)
            return
        self.pending = True
        self.window.busy(True)
        self.app.voice_reply.show_text("Estou pensando na sua pergunta...", 15000)
        threading.Thread(target=self._generate, args=(text,), daemon=True).start()

    def _perform(self, task):
        if task.kind == "open":
            open_application(task.value)
            names = {"calculator": "Calculadora", "notepad": "Bloco de Notas",
                     "browser": "navegador", "documents": "pasta Documentos"}
            return f"Pronto, pedi ao Windows para abrir {names[task.value]}."
        if task.kind == "note":
            notes = self.app.paths.notes
            notes.mkdir(parents=True, exist_ok=True)
            name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + uuid.uuid4().hex[:8] + ".txt"
            (notes / name).write_text(task.value + "\n", encoding="utf-8")
            return "Anotação guardada localmente: " + task.value
        actions = {"sleep": self.app.menu_sleep, "play": self.app.menu_place_ball,
                   "work": self.app.menu_pedir_trabalho, "store_ball": self.app.menu_store_ball}
        actions[task.value]()
        return {"sleep": "Vou tentar tirar um cochilo.", "play": "Pronto, vamos brincar com a bolinha!",
                "work": "Vou ver se estou disposto a trabalhar no meu notebook.",
                "store_ball": "Bolinha guardada."}[task.value]

    def _generate(self, text):
        try:
            answer = self.client.ask(text)
        except Exception as error:
            if not self.closed:
                self.failed.emit(str(error))
        else:
            if not self.closed:
                self.answered.emit(answer)

    def _answer(self, text):
        if self.closed:
            return
        self.pending = False
        self.window.busy(False)
        self.window.append("Nexus", text)
        if not self.app._congelado() and not self.app.hidden:
            self.app.voice_reply.show_text(text[:500], 15000)

    def _error(self, text):
        self._answer(text)

    def close(self):
        self.closed = True
        self.window.close()
