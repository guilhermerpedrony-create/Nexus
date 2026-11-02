"""Baixa o modelo aberto de reconhecimento uma vez; a escuta funciona offline."""

import hashlib
from pathlib import Path
import tempfile
import urllib.request
import zipfile

MODELS = {
    "vosk-model-small-en-us-0.15": "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498",
    "vosk-model-small-pt-0.3": "6e1ce909032e1afa7a88e68a3d628ecafff302bdf195befab308826c395e93b7",
}


def main():
    root = Path(__file__).resolve().parent.parent
    target = root / "models"
    target.mkdir(exist_ok=True)
    for model, checksum in MODELS.items():
        prepare(target, model, checksum)
    print("Pronto. Ative 'Ouvir quando eu chamar Nexus' nas Configuracoes.")


def prepare(target, model, checksum):
    if ((target / model / "am" / "final.mdl").exists()
            or (target / model / "final.mdl").exists()):
        print(f"Modelo ja instalado: {model}")
        return
    with tempfile.TemporaryDirectory(prefix="nexus-model-") as temp:
        archive = Path(temp) / "model.zip"
        print(f"Baixando modelo local: {model}...")
        urllib.request.urlretrieve(f"https://alphacephei.com/vosk/models/{model}.zip", archive)
        with archive.open("rb") as downloaded:
            digest = hashlib.file_digest(downloaded, "sha256").hexdigest()
        if digest != checksum:
            raise ValueError("O modelo baixado nao corresponde ao SHA256 verificado.")
        with zipfile.ZipFile(archive) as zipped:
            for entry in zipped.infolist():
                resolved = (target / entry.filename).resolve()
                if not resolved.is_relative_to(target.resolve()):
                    raise ValueError("Caminho invalido no modelo.")
            zipped.extractall(target)


if __name__ == "__main__":
    main()
