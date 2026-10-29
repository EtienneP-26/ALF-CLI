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
- **Année EPITECH** : ...
- **Objectif** : ...
- **Contraintes** : Language_imposé, librairies_authorisé_interdites, etc

Explication du projet.

## Installation
```bash
git clone https://github.com/EtienneP-26/ALF-CLI.git
cd ALF-CLI
```
 
## Utilisation
```bash
python3 src/alf [--model NAME] [--allowed-dir DIR]...
```
- `--model NAME` : modèle Ollama (défaut `gemma4:e2b-mt`).
- `--allowed-dir DIR` : dossier où `read_file`/`write_file` ont le droit d'aller (répétable, défaut : dossier courant). Hors de ces dossiers, l'accès est refusé.
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
