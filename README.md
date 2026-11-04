<p align="center"><img src="assets/logo.png" width="200"></p>

<h1 align="center">ALF-CLI</h1>

<p align="center"><em>Un agent de développement en ligne de commande, local et privé, propulsé par Ollama.</em></p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="Licence" src="https://img.shields.io/badge/licence-usage%20personnel-red">
  <img alt="Ollama" src="https://img.shields.io/badge/Ollama-local-black?logo=ollama&logoColor=white">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-compatible-1800f7">
</p>

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Commandes](#commandes)
- [Configuration](#configuration)
- [Sécurité](#sécurité)
- [Architecture](#architecture)
- [Tests](#tests)
- [Contribuer](#contribuer)
- [Licence](#licence)
- [Auteur](#auteur)

## Fonctionnalités

ALF-CLI (commande `alf`) est un agent conversationnel qui tourne dans votre terminal et utilise un modèle servi par [Ollama](https://ollama.com). Le modèle peut appeler des outils pour agir sur votre projet :

| Outil | Rôle |
| --- | --- |
| `read_file` | lire un fichier |
| `write_file` | créer ou écraser un fichier (diff affiché) |
| `edit_file` | remplacer un morceau de texte dans un fichier |
| `list_dir` | lister un dossier |
| `run_command` | exécuter une commande dans un conteneur Docker isolé |
| `web_search` | recherche web via DuckDuckGo |
| `plan_task` | annoncer un plan en étapes |

Et aussi :

- réponses en streaming rendues en Markdown (rich) ;
- affichage optionnel du raisonnement du modèle (`--think`) ;
- conversations sauvegardées, reprenables et renommables ;
- suivi de la fenêtre de contexte, avec alerte et compactage automatique par résumé des anciens messages ;
- serveurs MCP (format Claude Desktop) dont les outils sont ajoutés à l'agent ;
- mode `ask` (confirmation avant chaque action sensible) ou `auto`.

## Prérequis

- Python 3.10 ou plus récent
- [Ollama](https://ollama.com) installé et lancé, avec au moins un modèle téléchargé (par défaut `gemma4:e2b-mt`)
- [Docker](https://www.docker.com) pour le bac à sable de `run_command` (sinon utilisez `--no-sandbox`)
- `uvx` (outil `uv`) si vous gardez le serveur MCP `time` de `mcp_servers.json`

## Installation

```bash
git clone <url-du-depot> ALF-CLI
cd ALF-CLI
pip install -r requirements.txt

# image du bac à sable utilisée par run_command
docker build -t alf-sandbox .

# modèle par défaut
ollama pull gemma4:e2b-mt

# (optionnel) rendre la commande `alf` disponible partout
sudo ln -s "$PWD/bin/alf" /usr/local/bin/alf
```

Le lanceur `bin/alf` exécute `src/alf` quel que soit l'endroit d'où il est appelé.

## Utilisation

```bash
alf                                   # nouvelle conversation dans le dossier courant
alf --model qwen3:8b --think          # autre modèle, avec le raisonnement affiché
alf --continue                        # rouvrir la dernière conversation
alf --resume 2                        # rouvrir la conversation n°2 de /conversations
alf --allowed-dir ~/projet --allowed-dir ~/notes
alf --auto                            # ne rien demander avant d'agir
alf --no-sandbox                      # commandes directement sur la machine (risqué)
alf --mcp-config ./mcp_servers.json   # utiliser un fichier MCP précis
```

Options de `alf --help` :

| Option | Description |
| --- | --- |
| `--continue` | rouvrir la dernière conversation |
| `--resume ID_OR_NUMBER` | rouvrir une conversation par id ou par son numéro dans `/conversations` |
| `--max-tokens N` | budget de contexte envoyé au modèle (`num_ctx`), minimum 4096 ; par défaut la longueur de contexte du modèle, sinon 8192 |
| `--model NAME` | modèle Ollama (défaut : `gemma4:e2b-mt`) |
| `--think` | afficher le raisonnement du modèle, s'il le supporte |
| `--auto` | exécuter les commandes et écrire les fichiers sans demander |
| `--allowed-dir DIR` | dossier accessible aux outils (répétable, défaut : dossier courant) |
| `--no-sandbox` | exécuter les commandes sans Docker |
| `--mcp-config FILE` | configuration MCP, remplace `$ALF_HOME/mcp_servers.json` |

`--continue` et `--resume` sont mutuellement exclusifs.

## Commandes

Tapez-les dans l'invite de `alf` :

| Commande | Effet |
| --- | --- |
| `/help` | lister les commandes |
| `/exit` | quitter |
| `/model [nom]` | choisir un modèle (menu sans argument) |
| `/mode [ask\|auto]` | choisir le mode de confirmation |
| `/think [on\|off\|show]` | activer le raisonnement, ou afficher le dernier |
| `/new` | démarrer une nouvelle conversation |
| `/rename <titre>` | renommer la conversation courante |
| `/conversations` | lister les conversations sauvegardées, la plus récente d'abord |
| `/resume <numéro>` | reprendre une conversation |
| `/delete <numéro>` | supprimer une conversation (avec confirmation) |

## Configuration

### Variables d'environnement

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `ALF_HOME` | dossier de données (conversations, `mcp_servers.json`) | `~/.alf` |
| `OLLAMA_HOST` | adresse du serveur Ollama | `http://localhost:11434` |

Les conversations sont stockées en JSON dans `$ALF_HOME/conversations/`.

### Serveurs MCP

ALF-CLI lit `$ALF_HOME/mcp_servers.json` (ou le fichier donné par `--mcp-config`) au format Claude Desktop. Les outils de chaque serveur sont exposés au modèle sous le nom `<serveur>__<outil>`. Un serveur invalide ou en échec est signalé et ignoré, sans bloquer le démarrage.

Exemple fourni dans `mcp_servers.json` :

```json
{
  "mcpServers": {
    "devtools": {"command": "python3", "args": ["src/McpServers/DevTools.py"]},
    "time": {"command": "uvx", "args": ["mcp-server-time"]}
  }
}
```

`devtools` est un petit serveur du dépôt dont l'outil `find_todos` liste les commentaires TODO et FIXME du dossier courant.

## Sécurité

- **Dossiers autorisés** : les outils fichiers et `run_command` ne sortent pas des dossiers donnés par `--allowed-dir` (dossier courant par défaut).
- **Fichiers secrets** (`.env`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, etc.) : accès refusé.
- **Bac à sable** : `run_command` lance un conteneur `alf-sandbox` jetable, sans réseau, système de fichiers en lecture seule, 512 Mo de mémoire, 1 CPU, 100 processus maximum, toutes les capacités retirées, `.git` en lecture seule, secrets masqués, délai de 12 s. Si l'image ou Docker est absent, la commande est refusée.
- **Mode `ask`** : une confirmation est demandée avant d'agir ; `--auto` ou `/mode auto` la désactive.

## Architecture

```text
.
├── bin/alf                 # lanceur
├── src/
│   ├── alf                 # point d'entrée et boucle principale
│   ├── Variables.py        # logo, outils disponibles, constantes de contexte
│   ├── Context.py          # estimation et affichage de l'usage du contexte
│   ├── Memory.py           # sauvegarde des conversations (ALF_HOME)
│   ├── HandleResponse.py   # gestion des réponses et appels d'outils
│   ├── AlfTools/           # read/write/edit, run_command, web_search, plan_task,
│   │                       # permissions, client MCP
│   ├── CliTools/           # arguments et affichage (rich, prompt_toolkit)
│   ├── Commands/           # commandes slash (/help, /model, ...)
│   ├── OllamaTools/        # connexion, flux, modèles, résumé du contexte
│   └── McpServers/         # serveur MCP d'exemple (devtools)
├── tests/                  # tests pytest
├── docs/                   # documentation
├── assets/logo.png
├── mcp_servers.json        # exemple de configuration MCP
├── Dockerfile              # image alf-sandbox
└── docker-compose.yml
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

## Contribuer

Les contributions passent par une issue validée puis une branche partant de `dev`. Les règles complètes sont dans [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Usage personnel, tous droits réservés. Voir le fichier [LICENCE](LICENCE).

## Auteur

Etienne Pouille — [GitHub : EtienneP-26](https://github.com/EtienneP-26)
