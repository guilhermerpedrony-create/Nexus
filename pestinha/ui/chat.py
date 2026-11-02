"""Janela de conversa, com histórico apenas na memória desta sessão."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout

from .. import config
from .ui import STYLE, face_icon


class ChatWindow(QDialog):
    submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Conversar com {config.APP_NOME}")
        self.setWindowIcon(face_icon())
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setStyleSheet(STYLE + "QPlainTextEdit, QLineEdit { background: #10251b; color: #dfffe6; "
                           "border: 1px solid #2c5236; padding: 8px; font: 14px 'Segoe UI'; }")
        self.resize(480, 430)
        layout = QVBoxLayout(self)
        hint = QLabel("Fale Nexus e depois sua pergunta, ou escreva abaixo.\n"
                      "Você pode pedir: abra a calculadora, abra o bloco de notas ou anote: ...")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.document().setMaximumBlockCount(500)
        layout.addWidget(self.transcript)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Pergunte ou faça um pedido...")
        self.input.setMaxLength(4000)
        self.send = QPushButton("Enviar")
        self.input.returnPressed.connect(self._submit)
        self.send.clicked.connect(self._submit)
        row.addWidget(self.input)
        row.addWidget(self.send)
        layout.addLayout(row)
        self.status = QLabel("Respostas escritas · conversa local")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _submit(self):
        text = self.input.text().strip()
        if text:
            self.input.clear()
            self.submitted.emit(text)

    def append(self, who, text):
        # Texto simples: respostas do modelo nunca são HTML ou links executáveis.
        self.transcript.appendPlainText(f"{who}: {text}\n")

    def busy(self, value):
        self.send.setEnabled(not value)
        self.input.setEnabled(not value)
        self.status.setText("Pensando..." if value else "Respostas escritas · conversa local")
