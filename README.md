# **ALF-CLI**

> This is an agentic CLI assistant powered by various tools. It operates by using defined tools to perform tasks, making it a powerful agent for command-line operations.

## Sommaire

- [Description](#description)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Architecture](#architecture)
- [Tests](#tests)
- [Bonus](#bonus)
- [Équipe](#équipe)

## Description
- **Année EPITECH** : 3ème année
- **Objectif** : ...
- **Contraintes** : Language_imposé, librairies_authorisé_interdites, etc

Explication du projet.

## Installation
```bash
git clone https://github.com/EtienneP-26/ALF-CLI.git
cd ALF-CLI
docker build -t alf-sandbox .
```
Docker est requis pour `run_command`. L'image `alf-sandbox` contient Python, C/C++ et git ; tout autre outil doit être ajouté au `Dockerfile`, car le conteneur n'a pas de réseau.
 
## Utilisation
```bash
python3 src/alf [--model NAME] [--allowed-dir DIR]... [--max-tokens N] [--no-sandbox]
```
- `--model NAME` : modèle Ollama (défaut `gemma4:e2b-mt`).
- `--allowed-dir DIR` : dossier où `read_file`, `list_dir`, `write_file`, `edit_file` et `run_command` ont le droit d'aller (répétable, défaut : dossier courant). Hors de ces dossiers, l'accès est refusé. `run_command` s'exécute dans un conteneur Docker jetable : pas de réseau, seuls ces dossiers sont visibles (`.git` en lecture seule), 512 Mo de mémoire, 1 CPU, 100 processus, 12 s maximum. Sans Docker ou sans l'image, la commande est refusée et rien ne tourne sur la machine. Un filtre sur le texte de la commande s'y ajoute : un chemin absolu comme `/usr/bin/x` est refusé, `/dev/null` est permis. Les fichiers secrets (`.env`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`…, sauf `.env.example`) sont bloqués en lecture (`read_file`, `edit_file`, noms dans `run_command`) ; la liste est courte et le filtre contournable (`cat .e*` ou `python3 -c ...` passent). `list_dir` liste un dossier sans lire les fichiers. `read_file` refuse les fichiers de plus de 1 Mo et les fichiers binaires.
- `--max-tokens N` : budget de tokens du contexte envoyé au modèle (`num_ctx` d'Ollama), défaut : le contexte max du modèle Ollama (8192 si inconnu), minimum 4096. C'est le plafond du contexte : une ligne `Context: 0.8k/131.1k (0%)` (en kTokens) s'affiche après chaque tour, avec une alerte à partir de 80 %.
- `--auto` : `run_command`, `write_file` et `edit_file` s'exécutent sans confirmation (mode `ask` par défaut). `/mode [ask|auto]` ouvre un choix entre `ask` et `auto`, ou change directement le mode.
- `--no-sandbox` : `run_command` s'exécute directement sur la machine, sans Docker, avec un avertissement au lancement. Il ne reste que le filtre sur le texte de la commande, qui est contournable (ex. `python3 -c 'print(open("/etc/passwd").read())'`). Utile dans un conteneur sans Docker, comme le service `env` de `docker-compose.yml` ; à éviter ailleurs, surtout avec `--auto`.
- `plan_task` : outil du modèle qui présente un plan numéroté avant une tâche à plusieurs étapes ; il passe par la même approbation (refus possible en `ask`).
- Ollama injoignable ou modèle absent : message clair et code de sortie 1.
- Une saisie vide est ignorée.
- Mémoire : chaque conversation est enregistrée en entier dans `~/.alf/conversations/<id>.json` (`$ALF_HOME` pour changer), avec son id, son titre (tiré du premier message) et ses dates de création et de dernière activité. Une nouvelle conversation démarre à chaque lancement. `/new` en démarre une autre, `/rename <titre>` renomme la conversation courante, `/conversations` liste les conversations enregistrées et `/resume <numéro>` en rouvre une. Au lancement, `--continue` rouvre la dernière conversation et `--resume <id ou numéro>` en rouvre une précise.

Exemples:
```bash
>>> ./nom_du_binaire [options] arguments
>>> Hello, World!
```
Ou
```bash
>>> ./nom_du_binaire [options] arguments
>>> Hello, World!
```

## Architecture
```
.
├── .git/hooks/                 # (Ces fichiers ne sont pas commits/trackés)
│   ├── commit-msg              # Vérification du nom de commit 
│   └── pre-commit              # Vérification pre-commits (Ce fichier n'est pas commit)
├── .github/workflows/ci.yml    # CI/CD Github
├── src/                        # Code source
├── tests/                      # Tests fonctionnels/unitaires
├── docs/                       # Documentation complémentaire
├── scripts/                    # Scripts
│   └── new-branch              # Script to create new git branches
│
├── .gitignore                  # Fichiers à ne pas Commit
├── docker-compose.yml          # Environnement de test Docker (Epitech)
├── README.md                   # Description rapide du projet
└── CONTRIBUTING.md             # Guide pour les contributeurs
```

## Tests
```bash
pytest --cov=.
```
 
## Bonus
Liste des features bonus implémentées, avec un lien vers le fichier/la fonction concernée.
 
## Équipe
| Nom | Rôle | GitHub |
|---|---|---|
| Etienne Pouille | ... | Etiennep-26 |
| Pierric Buchez | ... | MyEcoria |
| Maximilien Lachevre Leconte | ... | maxlabinche |
