# Meu Pestinha

Este e o fork pessoal para desenvolver e guardar melhorias:
https://github.com/guilhermerpedrony-create/pestinha

O projeto original continua em https://github.com/mille-okws/pestinha.

## Continuar em outro PC

Abra o Codex e envie:

> Baixe https://github.com/guilhermerpedrony-create/pestinha, leia MEU-PROJETO.md e configure o Pestinha neste PC. Quero continuar desenvolvendo minha versao. Ao concluir as melhorias que eu solicitar, salve com commit e push neste repositorio.

Para instalar a distribuicao Windows original verificada, execute `setup/Instalar-Pestinha.cmd`. Precisa de Windows 10/11 de 64 bits e internet. Instala em `%LOCALAPPDATA%\Programs\Pestinha`, preserva a pasta `memory/` existente e cria atalhos. O perfil inicial usa Bryan e as opcoes padrao do projeto, com modo teste e travessuras desligados.

Esse instalador usa um executavel fixo da revisao original `25fd74be2aeab6935bf8a7459963374f48d5d28b`. Alteracoes futuras no codigo precisam ser executadas pelo Python ou empacotadas novamente; esse executavel nao incorpora alteracoes automaticamente.

## Desenvolver a versao atual do fork

Instale Python compativel com `requirements.txt` (minimo 3.11; prefira 3.13 de 64 bits), crie um ambiente virtual e rode, na raiz do repositorio:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Para testes, instale tambem `requirements-dev.txt` no mesmo ambiente e siga `CONTRIBUTING.md`. Para distribuir um executavel com as melhorias, siga a secao de builds do README original ou o workflow `.github/workflows/executaveis.yml`.

## Salvar e recuperar melhorias

`origin` deve apontar para este fork; `upstream` aponta para o projeto original. Commit salva um marco local; push envia esse marco ao GitHub. Verifique `git status` antes de concluir e confirme que o commit foi enviado. Em outro computador, clone este fork ou atualize uma copia existente com `git pull --ff-only` depois de verificar alteracoes locais.

## Memoria do bichinho

O GitHub guarda o codigo e as personalizacoes versionadas. O aprendizado e a rotina ficam em `memory/`, ignorada pelo Git. Para levar esses dados, feche o Pestinha e faca backup privado dessa pasta. Na instalacao Windows ela fica em `%LOCALAPPDATA%\Programs\Pestinha\memory`; no modo Python fica na raiz do checkout. Restaure a copia com o programa fechado. Cada PC mantem seu estado; nao ha sincronizacao automatica.
