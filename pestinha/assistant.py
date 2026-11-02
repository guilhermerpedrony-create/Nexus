"""Conversa local e pedidos explícitos. Texto do modelo nunca vira comando do sistema."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.request

MODEL = "qwen2.5:3b-instruct"
BASE_URL = "http://127.0.0.1:11434"
SYSTEM_PROMPT = (
    "Você é Nexus, um companheiro de desktop que conversa em português brasileiro. "
    "Responda diretamente à pergunta, de forma útil e breve, em até 120 palavras. "
    "Você não tem acesso à internet, arquivos, tela ou programas. Não invente informações atuais. "
    "Se não souber, diga. Nunca afirme ter executado uma ação. O aplicativo executa separadamente "
    "apenas pedidos explícitos para abrir Calculadora, Bloco de Notas, navegador ou pasta Documentos, "
    "guardar uma anotação, dormir, brincar, trabalhar, mostrar ou guardar a bolinha. "
    "Para outras tarefas, explique como fazer. Não use blocos de raciocínio ou tags think."
)


def normalized(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip(" .,!?\n\t")


@dataclass(frozen=True)
class Task:
    kind: str
    value: str = ""


def requested_task(text):
    """Aceita imperativos específicos; perguntas e exemplos continuam sendo conversa."""
    plain = normalized(text)
    plain = re.sub(r"^(?:oi |ei )?(?:nexus|neksus)[, ]*", "", plain)
    plain = re.sub(r"^(?:por favor,? )", "", plain)
    plain = re.sub(r",? por favor$", "", plain)
    plain = re.sub(r" (?:pra|para) mim$", "", plain)
    applications = {
        "calculadora": "calculator", "o calculadora": "calculator", "a calculadora": "calculator",
        "bloco de notas": "notepad", "o bloco de notas": "notepad",
        "navegador": "browser", "o navegador": "browser",
        "documentos": "documents", "a pasta documentos": "documents", "pasta documentos": "documents",
    }
    match = re.fullmatch(r"(?:(?:voce|vc) )?(?:(?:pode|consegue) )?(?:abra|abre|abrir|inicie|inicia|iniciar) (.+)", plain)
    if match and match[1] in applications:
        return Task("open", applications[match[1]])
    note = re.match(r"^(?:nexus[, ]+)?(?:anote|anota|guarde uma anotação|guarde uma anotacao)\s*[:,-]?\s+(.+)$",
                    text.strip(), flags=re.IGNORECASE | re.DOTALL)
    if note and note[1].strip():
        return Task("note", note[1].strip()[:4000])
    pet_actions = {
        "durma": "sleep", "dorme": "sleep", "va dormir": "sleep",
        "brinque": "play", "brinca": "play", "jogue a bolinha": "play",
        "trabalhe": "work", "trabalha": "work",
        "mostre a bolinha": "play", "mostra a bolinha": "play",
        "guarde a bolinha": "store_ball", "guarda a bolinha": "store_ball",
    }
    if plain in pet_actions:
        return Task("pet", pet_actions[plain])
    return None


def open_application(app):
    """Somente nomes conhecidos; nunca aceita linha de comando produzida pelo modelo."""
    system = Path(os.environ.get("SystemRoot", "C:/Windows"))
    commands = {
        "calculator": [str(system / "System32" / "calc.exe")],
        "notepad": [str(system / "System32" / "notepad.exe")],
        "documents": [str(system / "explorer.exe"), str(Path.home() / "Documents")],
    }
    if app == "browser":
        import webbrowser
        if not webbrowser.open("https://www.google.com/"):
            raise RuntimeError("Não foi possível abrir o navegador padrão.")
        return
    if app not in commands:
        raise ValueError("Programa não disponível.")
    subprocess.Popen(commands[app], shell=False)


class LocalChat:
    def __init__(self, root, model=MODEL):
        self.root = Path(root)
        self.model = model
        self.history = []
        # O endpoint é HTTP de loopback. Não cria contexto TLS, não consulta proxies
        # e não segue redirecionamentos para fora do servidor local.
        self.http = urllib.request.OpenerDirector()
        for handler in (urllib.request.HTTPHandler(), urllib.request.HTTPDefaultErrorHandler(),
                        urllib.request.HTTPErrorProcessor(), urllib.request.UnknownHandler()):
            self.http.add_handler(handler)
        self.server = None

    def _json(self, route, data=None, timeout=90):
        request = urllib.request.Request(BASE_URL + route,
                                         data=None if data is None else json.dumps(data).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        with self.http.open(request, timeout=timeout) as response:
            return json.load(response)

    def ensure_server(self):
        try:
            self._json("/api/version", timeout=1)
            return
        except (OSError, urllib.error.URLError):
            pass
        executable = self.root / "ai" / "ollama.exe"
        if not executable.is_file():
            raise RuntimeError("A conversa local ainda não foi preparada. Execute setup/Preparar-Conversa.ps1.")
        if self.server is None or self.server.poll() is not None:
            env = os.environ.copy()
            env.update(OLLAMA_HOST="127.0.0.1:11434", OLLAMA_NO_CLOUD="1",
                       OLLAMA_MODELS=str(self.root / "models" / "ollama"), OLLAMA_NUM_PARALLEL="1")
            self.server = subprocess.Popen([str(executable), "serve"], env=env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(40):
            try:
                self._json("/api/version", timeout=1)
                return
            except (OSError, urllib.error.URLError):
                time.sleep(0.25)
        raise RuntimeError("A IA local não iniciou. Tente novamente em alguns segundos.")

    def ask(self, question):
        self.ensure_server()
        question = question.strip()[:4000]
        if not question:
            raise ValueError("Escreva ou fale uma pergunta.")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history[-12:],
                    {"role": "user", "content": question}]
        try:
            result = self._json("/api/chat", {
                "model": self.model, "messages": messages, "stream": False,
                "keep_alive": "5m", "options": {"num_ctx": 4096, "num_predict": 256, "temperature": 0.6},
            })
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise RuntimeError("Modelo de conversa ausente. Execute setup/Preparar-Conversa.ps1.") from error
            raise RuntimeError("A IA local encontrou um problema ao responder. Tente novamente.") from error
        except (OSError, urllib.error.URLError) as error:
            raise RuntimeError("A IA local demorou ou não está disponível. Tente novamente.") from error
        answer = result.get("message", {}).get("content", "").strip()
        if "</think>" in answer:
            answer = answer.rsplit("</think>", 1)[-1].strip()
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
        if not answer:
            raise RuntimeError("A IA não retornou uma resposta. Tente reformular a pergunta.")
        self.history = [*self.history[-10:], {"role": "user", "content": question},
                        {"role": "assistant", "content": answer}]
        return answer[:6000]
