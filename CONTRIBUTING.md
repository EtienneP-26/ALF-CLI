# Contribuer

Merci de votre intérêt ! Les contributions sont les bienvenues, selon le
processus ci-dessous.

## Avant de commencer

1. **Ouvrez une issue** qui décrit ce que vous voulez faire (nouvelle
   fonctionnalité, correction, amélioration).
2. **Attendez la validation** du mainteneur avant de coder.
3. Demandez un accès au dépôt si vous n'en avez pas (les forks sont
   interdits par la licence).

## Workflow

Toutes les branches partent de `dev`, jamais de `main`.

```bash
git checkout dev
git pull origin dev
git checkout -b feat/nom-court-de-la-fonctionnalite
```

Conventions de nommage :

- `feat/...` : nouvelle fonctionnalité
- `fix/...` : correction de bug
- `docs/...` : documentation

Ensuite :

1. Faites vos commits (messages clairs, un sujet par commit).
2. Poussez votre branche : `git push origin feat/nom-court`.
3. Ouvrez une Pull Request **vers `dev`** (jamais vers `main`) en
   décrivant ce qui a été fait et en référençant l'issue (`Closes #12`).
4. Attendez la relecture. Des modifications peuvent être demandées.

## Règles

- Une PR = un sujet.
- Pas de push direct sur `main` ni `dev`.
- `main` est mise à jour uniquement par le mainteneur, depuis `dev`.
- En contribuant, vous acceptez l'article 5 de la [LICENSE](./LICENSE).
