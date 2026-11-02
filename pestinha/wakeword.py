"""Detecção da chamada em texto temporário; não armazena áudio nem transcrições."""

import re
import unicodedata


def called_nexus(text):
    """Aceita o nome e a grafia fonética, sem disparar para palavras parecidas."""
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return bool(set(re.findall(r"[a-z]+", normalized)) & {"nexus", "neksus"})


class WakeGate:
    """Um disparo por enunciado, com intervalo para não responder a ecos."""

    def __init__(self, cooldown=5.0):
        self.cooldown = cooldown
        self.last = float("-inf")
        self.latched = False

    def accept(self, text, now, final=False):
        triggered = called_nexus(text) and not self.latched and now - self.last >= self.cooldown
        if triggered:
            self.last = now
            self.latched = True
        if final:
            self.latched = False
        return triggered
