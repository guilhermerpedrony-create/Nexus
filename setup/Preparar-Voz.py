"""Baixa o modelo aberto de reconhecimento uma vez; a escuta funciona offline."""

import hashlib
from pathlib import Path
import tempfile
import urllib.request
import zipfile

MODEL = "vosk-model-small-en-us-0.15"
URL = f"https://alphacephei.com/vosk/models/{MODEL}.zip"
SHA256 = "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"


def main():
    root = Path(__file__).resolve().parent.parent
    target = root / "models"
    if (target / MODEL / "am" / "final.mdl").exists():
        print("Modelo de voz ja instalado.")
        return
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nexus-model-") as temp:
        archive = Path(temp) / "model.zip"
        print("Baixando modelo local para reconhecer Nexus (40 MB)...")
        urllib.request.urlretrieve(URL, archive)
        with archive.open("rb") as downloaded:
            digest = hashlib.file_digest(downloaded, "sha256").hexdigest()
        if digest != SHA256:
            raise ValueError("O modelo baixado nao corresponde ao SHA256 verificado.")
        with zipfile.ZipFile(archive) as zipped:
            for entry in zipped.infolist():
                resolved = (target / entry.filename).resolve()
                if not resolved.is_relative_to(target.resolve()):
                    raise ValueError("Caminho invalido no modelo.")
            zipped.extractall(target)
    print("Pronto. Ative 'Ouvir quando eu chamar Nexus' nas Configuracoes.")


if __name__ == "__main__":
    main()
