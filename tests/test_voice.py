"""Chamada, repetição, limites de privacidade e resposta sem microfone real."""

import os
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from pestinha.wakeword import WakeGate, called_nexus
from pestinha.voice import VoiceListener, VoiceReply


def test_nome_com_limites_e_acentos():
    for text in ["Nexus", "oi, néxus!", "Néksus vem aqui"]:
        assert called_nexus(text)
    for text in ["", "anexus", "nexusinho", "nexo", "o próximo", "oi amigo"]:
        assert not called_nexus(text)


def test_parciais_nao_repetem_e_respeitam_intervalo():
    gate = WakeGate()
    assert gate.accept("nexus", 0)
    assert not gate.accept("nexus vem", 1)
    assert not gate.accept("nexus", 6, final=True)
    assert gate.accept("nexus", 7, final=True)
    assert not gate.accept("nexus", 8, final=True)
    assert gate.accept("nexus", 13, final=True)


def test_sem_modelo_informa_erro_sem_abrir_microfone(tmp_path):
    QApplication.instance() or QApplication([])
    listener = VoiceListener(tmp_path)
    errors = []
    listener.failed.connect(errors.append)
    listener.start()
    listener._thread.join(timeout=3)
    QApplication.processEvents()
    assert not listener.active
    assert len(errors) == 1 and "Modelo de voz ausente" in errors[0]
    previous_thread = listener._thread
    listener.start()  # não fica tentando repetidamente depois de falhar
    assert listener._thread is previous_thread
    listener.close()


def test_balao_para_ao_desativar_sem_voz_do_sistema():
    QApplication.instance() or QApplication([])
    from PySide6.QtWidgets import QWidget
    pet = QWidget()
    reply = VoiceReply(pet)
    reply.respond(aloud=False)
    assert reply.bubble.isVisible()
    assert reply.speaker is None
    reply.stop()
    assert not reply.bubble.isVisible()
    reply.close()
    pet.close()


def test_chamada_ignorada_em_panico_e_quando_microfone_desligado():
    from pestinha.app import PestinhaApp
    app = Mock()
    app._congelado.return_value = True
    PestinhaApp.on_voice_call(app)
    app.menu_poke.assert_not_called()
    app._congelado.return_value = False
    app.hidden = False
    app.pet.isVisible.return_value = True
    app.perms = {"ouvir_nome": False}
    PestinhaApp.on_voice_call(app)
    app.menu_poke.assert_not_called()


def test_modelo_fica_ao_lado_do_programa():
    QApplication.instance() or QApplication([])
    listener = VoiceListener(Path("example"))
    assert listener.model_path == Path("example/models/vosk-model-small-en-us-0.15")


def test_pausar_esconder_e_panico_param_a_escuta(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import pestinha.app as app_module
    from pestinha.paths import Paths
    from pestinha.settings_store import SettingsStore

    QApplication.instance() or QApplication([])
    microphone = Mock()
    microphone.called = Mock()  # Mock.called é um booleano reservado; aqui é um sinal Qt.
    response = Mock()
    monkeypatch.setattr(app_module, "VoiceListener", lambda *args: microphone)
    monkeypatch.setattr(app_module, "VoiceReply", lambda *args: response)
    monkeypatch.setattr(app_module, "PanicHotkey", lambda: SimpleNamespace(ok=True, pressed=Mock()))
    monkeypatch.setattr(app_module.senses, "is_fullscreen", lambda: False)
    app = app_module.PestinhaApp(SettingsStore(Paths(tmp_path)), Paths(tmp_path))
    app.apply_perms({"ouvir_nome": True})
    microphone.start.assert_called()
    app.toggle_pause()
    microphone.stop.assert_called()
    microphone.reset_mock()
    app.toggle_pause()
    microphone.start.assert_called()
    app.toggle_hidden()
    microphone.stop.assert_called()
    microphone.reset_mock()
    app.toggle_hidden()
    microphone.start.assert_called()
    app.panic()
    microphone.stop.assert_called()
    response.stop.assert_called()
    app.tray.icon.hide()
