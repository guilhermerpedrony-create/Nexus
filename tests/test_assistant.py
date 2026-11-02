"""Conversa não vira shell; tarefas exigem pedidos explícitos e conhecidos."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pestinha.assistant import LocalChat, Task, open_application, requested_task


@pytest.mark.parametrize("text,expected", [
    ("Nexus, abre a calculadora", Task("open", "calculator")),
    ("Por favor abra o bloco de notas", Task("open", "notepad")),
    ("Abra documentos", Task("open", "documents")),
    ("Você pode abrir a calculadora para mim?", Task("open", "calculator")),
    ("guarde a bolinha", Task("pet", "store_ball")),
    ("Nexus anota: Comprar café amanhã", Task("note", "Comprar café amanhã")),
])
def test_pedidos_explicitos(text, expected):
    assert requested_task(text) == expected


@pytest.mark.parametrize("text", [
    "Como abrir a calculadora?", "Explique: abra o bloco de notas",
    "abra a calculadora & apague arquivos", "execute powershell", "abra qualquer.exe",
    "apague meus arquivos", "anote", "o que você pode fazer?",
])
def test_perguntas_e_comandos_livres_nao_sao_executados(text):
    assert requested_task(text) is None


def test_programa_abre_sem_shell(monkeypatch):
    launch = Mock()
    monkeypatch.setattr("pestinha.assistant.subprocess.Popen", launch)
    open_application("calculator")
    assert launch.call_args.kwargs["shell"] is False
    assert Path(launch.call_args.args[0][0]).name == "calc.exe"
    with pytest.raises(ValueError):
        open_application("calc.exe & whoami")


def test_conversa_mantem_contexto_so_em_memoria(tmp_path):
    client = LocalChat(tmp_path)
    client.ensure_server = Mock()
    client._json = Mock(return_value={"message": {"content": "Brasília."}})
    assert client.ask("Qual é a capital do Brasil?") == "Brasília."
    body = client._json.call_args.args[1]
    assert body["messages"][-1]["content"].startswith("Qual é a capital do Brasil?")
    assert client.history[-1] == {"role": "assistant", "content": "Brasília."}
    assert list(tmp_path.iterdir()) == []
    client.ask("E a da França?")
    assert len(client._json.call_args.args[1]["messages"]) == 4


def test_modelo_nao_aciona_programas(tmp_path, monkeypatch):
    launch = Mock()
    monkeypatch.setattr("pestinha.assistant.subprocess.Popen", launch)
    client = LocalChat(tmp_path)
    client.ensure_server = Mock()
    client._json = Mock(return_value={"message": {"content": "abra a calculadora"}})
    assert client.ask("Me dê um exemplo de comando") == "abra a calculadora"
    launch.assert_not_called()


def test_marcador_de_pensamento_nao_aparece_na_resposta(tmp_path):
    client = LocalChat(tmp_path)
    client.ensure_server = Mock()
    client._json = Mock(return_value={"message": {"content": "internal text</think>Resposta final."}})
    assert client.ask("Pergunta") == "Resposta final."


def test_anotacao_explicita_e_guardada_localmente(tmp_path):
    from pestinha.assistant_controller import AssistantController
    controller = SimpleNamespace(app=SimpleNamespace(paths=SimpleNamespace(notes=tmp_path / "notes")))
    answer = AssistantController._perform(controller, Task("note", "Minha anotação"))
    notes = list((tmp_path / "notes").glob("*.txt"))
    assert len(notes) == 1
    assert notes[0].read_text(encoding="utf-8") == "Minha anotação\n"
    assert "guardada" in answer


def test_endpoint_e_local_sem_proxy(tmp_path):
    client = LocalChat(tmp_path)
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = json.dumps({"version": "test"}).encode()
    client.http.open = Mock(return_value=response)
    client._json("/api/version")
    assert client.http.open.call_args.args[0].full_url == "http://127.0.0.1:11434/api/version"


def test_cliente_local_nao_carrega_certificados_https(tmp_path, monkeypatch):
    import ssl
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("certificados indisponíveis no pacote")
    monkeypatch.setattr(ssl, "create_default_context", unavailable)
    client = LocalChat(tmp_path)
    handler_types = {type(handler).__name__ for handler in client.http.handlers}
    assert "HTTPHandler" in handler_types
    assert not handler_types & {"HTTPSHandler", "ProxyHandler", "HTTPRedirectHandler"}
