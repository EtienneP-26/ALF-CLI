# ALF-CLI : feuille de route

## Objectif

ALF-CLI ne fonctionne aujourd'hui qu'avec un Ollama local et des modèles qui gèrent les outils (tools). Cette feuille de route prévoit trois choses. D'abord, on doit pouvoir discuter avec n'importe quel modèle, même sans outils. Ensuite, on doit pouvoir viser un serveur distant ou un autre moteur : llama.cpp, vLLM, LM Studio, ou une API compatible OpenAI. Enfin, le projet doit devenir plus simple à installer et plus robuste, sans casser ce qui marche déjà.

Effort : **S** < 1 jour, **M** 1 à 3 jours, **L** plus de 3 jours.

---

## 1. Modèles sans outils (ex. `gemma2:2b`)

**Constat.** `getResponse` envoie toujours `tools=` (`src/OllamaTools/ResponseHandle.py:226-233`). Ollama répond alors `ResponseError "... does not support tools"`. L'erreur est attrapée dans `src/alf:111`, puis l'historique est annulé. Résultat : on ne peut pas discuter du tout avec ce modèle.

### 1a. Détection et repli en chat simple (S)
- **Quoi.**
  - Ajouter `supportsTools(client, model)` dans `src/OllamaTools/ModelContext.py`. Cette fonction lit `"tools" in client.show(model).capabilities`, sur le modèle de `supportsThinking`.
  - Ajouter un champ `toolMode` à `State` (`src/Commands/registry.py`). Le calculer au démarrage (`src/alf`) et à chaque `/model` (`src/Commands/builtin.py:108-126`).
  - Repli de sécurité : dans `getResponse`, si on reçoit `ResponseError` avec "does not support tools", relancer une fois avec `tools=[]` et le signaler une seule fois.
  - Prévoir un second prompt système sans la section « Tools » ni la boucle agentique. Aujourd'hui, `SystemPrompt` cite les outils en dur (`ResponseHandle.py:188`).
- **Pourquoi.** Se servir de `capabilities` évite un aller-retour en erreur. Le repli couvre les versions anciennes d'Ollama et les autres moteurs.
- **Limites.** Dans ce mode, le modèle ne peut plus agir sur le projet. Il faut le dire à l'utilisateur, par exemple « mode chat : outils désactivés ».

### 1b. Outils par prompt, en JSON dans le texte (M)
- **Quoi.**
  - Nouvelle option `--tool-mode auto|native|prompt|off`.
  - En mode `prompt`, le prompt système décrit chaque outil avec son schéma JSON. On le génère à partir des `tools` : fonctions Python et `ollama.Tool` du MCP.
  - On demande au modèle de répondre par un bloc ` ```tool {"name": ..., "arguments": {...}}``` `.
  - Nouveau module `src/OllamaTools/PromptTools.py`. Il analyse le texte après `collectStream` et fabrique des `Message.ToolCall`. Ainsi, **la boucle de `HandleResponse.py` reste la même**.
  - Au renvoi au modèle, les messages `tool` deviennent des messages `user` « Observation (read_file) : … ». En effet, les gabarits (templates) des modèles sans outils ignorent le rôle `tool`.
  - Dans `thinkVisual` (`src/CliTools/Cli.py:191`), masquer l'affichage à partir de ` ```tool `.
- **Limites.** Les petits modèles (2B) produisent souvent du JSON invalide. Il faut une relance avec l'erreur d'analyse, au plus une fois. La fiabilité restera bien en dessous des outils natifs.
- **Dépendances.** Aucune.

---

## 2. Machines distantes

### 2a. Modèle distant (S)
- **Quoi.** Aujourd'hui, seul `OLLAMA_HOST` est lu (`src/OllamaTools/ConnectionOllama.py:4`). On ajoute :
  - les options `--host URL`, `--ca-cert FILE`, `--timeout S` ;
  - une clé d'API lue dans la variable d'environnement `ALF_API_KEY`, envoyée comme en-tête `Authorization: Bearer` ;
  - TLS par une URL en `https://`.

  `ollama.Client(host, headers=..., timeout=httpx.Timeout(connect=5, read=300), verify=ca)` passe déjà ces réglages à httpx. Le client doit être créé dans une fabrique appelée après `parseArgs`, et non plus au moment de l'import.
- **Tunnel SSH.**
  - Documenter `ssh -N -L 11434:localhost:11434 user@gpu`. Ollama n'a pas d'authentification : ne jamais l'exposer sur `0.0.0.0`.
  - En option, `--ssh-tunnel user@host` lance ce tunnel avec `subprocess` et le ferme à la sortie. Effort S.
- **Impact sécurité.**
  - Le contenu des fichiers lus, les sorties de commandes et l'historique partent sur le réseau. La promesse « local et privé » du README ne tient plus.
  - Il faut un avertissement au démarrage si l'hôte n'est pas en boucle locale (loopback).
  - Pas de `--api-key` en option de ligne de commande : la clé serait visible dans `ps` et dans l'historique du shell.

### 2b. Exécution distante (L, expérimental)
- **Quoi.** Lancer `run_command` et les outils fichiers sur une machine distante par SSH, avec une option `--exec-host`.
- **Où.** Il faut toucher :
  - `AlfTools/RunCommand.py` : `ssh host -- docker run ...` ;
  - `AlfTools/FileManipulation.py` ;
  - `AlfTools/Permissions.py`. `check_path` utilise `os.path.realpath` en local et doit faire ce contrôle côté distant.
- **Limites et risques.**
  - Le sandbox et les règles sur les secrets doivent être refaits à distance, et la vérification de la clé d'hôte SSH doit être stricte.
  - L'agent SSH ne doit pas être transmis (pas de forwarding).
  - Une fuite de chemins entre la machine locale et la distante est possible.
  - `paramiko` serait une nouvelle dépendance. Le binaire `ssh` suffit.
- **Alternative recommandée.** Installer `alf` sur la machine distante (voir le point 4, pipx) et s'y connecter par SSH. Le coût est nul et le modèle de sécurité reste le même.

---

## 3. Autres moteurs et abstraction « provider »

- **Quoi.** Nouveau paquet `src/Providers/` qui contient :
  - `base.py` : l'interface `Provider` avec `chat(messages, tools, think, stream, on_text, on_thinking) -> ChatResponse`, `list_models()`, `capabilities(model)`, `context_length(model)` et `unload(model)` (optionnelle) ;
  - `ollama.py`, qui reprend le code actuel ;
  - `openai_compat.py` pour `/v1/chat/completions`. Il couvre llama.cpp (`--jinja`), vLLM (`--enable-auto-tool-choice --tool-call-parser`), LM Studio et les API cloud.
- **Format normalisé.** On garde les types `ollama.Message` / `ChatResponse` comme format interne. Ainsi, `HandleResponse.py`, `Memory._serialize` et `Context.py` ne changent pas.

| Point | Ollama | Compatible OpenAI |
|---|---|---|
| Arguments d'appel d'outil | `dict` | chaîne JSON, `id` obligatoire |
| Résultat d'outil | `tool_name` | `tool_call_id` (à générer et conserver) |
| Streaming | appels d'outils complets par fragment | deltas SSE, à rassembler par `index` |
| Raisonnement | `message.thinking`, `think=` | `reasoning_content` (vLLM, llama.cpp) ou balises `<think>` dans le texte |
| Jetons | `prompt_eval_count` / `eval_count` | `usage` (`stream_options.include_usage`) |
| Contexte | `options.num_ctx` | fixé par le serveur (`/props` pour llama.cpp, `max_model_len` pour vLLM) |
| Capacités | `/api/show` | aucune norme : on suppose les outils disponibles, avec repli 1a |

- **Fichiers à modifier.**
  - `ConnectionOllama.py`, à remplacer par une fabrique ;
  - `ResponseHandle.py` ;
  - `Summarize.py:51` ;
  - `ModelContext.py` ;
  - `HandleResponse.py:9-18` pour le décompte des jetons ;
  - `builtin.py` pour `/model` ;
  - `src/alf` : exceptions `ollama.ResponseError` à remplacer par `ProviderError`, et `keep_alive=0` (ligne 131) à remplacer par `unload()`.
- **Migration.**
  1. Créer `OllamaProvider` en déplaçant le code, sans changer le comportement. Les tests existants doivent passer.
  2. Ajouter `--provider ollama|openai` et `--base-url`.
  3. Ajouter le provider OpenAI-compatible, avec des tests sur des réponses SSE enregistrées.
- **Choix : httpx (déjà présent via ollama) plutôt que le SDK `openai`.**
  - Ce que ça apporte : aucune nouvelle dépendance.
  - Limite : il faut écrire un petit analyseur SSE (environ 60 lignes) et gérer les relances soi-même.
  - Le SDK `openai` serait plus robuste, mais c'est une dépendance de plus, à votre choix.
- **Effort.** L.

---

## 4. Autres améliorations

| Sujet | Quoi | Où | Effort |
|---|---|---|---|
| Fichier de config | `~/.alf/config.toml` avec des profils (`provider`, `url`, `model`, `api_key_env`, `tool_mode`). Priorité : option > variable d'env > profil > défaut. Commande `/profile <nom>`. | `CliTools/Args.py`, nouveau `Config.py` | M |
| Mode non interactif | `alf -p "..."` et lecture de stdin (`cat log \| alf -p "explique"`). Sans `--auto`, les actions sensibles sont **refusées** (pas d'invite possible). | `src/alf`, `Args.py` | S |
| Liste des modèles | `/model` utilise la liste figée au démarrage (`builtin.py:115`). Ajouter `/model refresh`. | `builtin.py` | S |
| Robustesse | Délais (aujourd'hui aucun, donc un hôte mort bloque indéfiniment). Relances avec attente croissante sur erreur de connexion, 429 ou 5xx, **seulement avant le premier fragment** reçu. | provider | S |
| Paramètres en dur | `MAXLOOP=10` (`HandleResponse.py:38`) et troncature à 5000 caractères (`:93`) à rendre configurables. | `Variables.py` | S |
| Packaging | `pyproject.toml` avec `[project.scripts] alf=...` pour installer par `pipx install`. Les modules au premier niveau (`Variables`, `Memory`, `Context`) doivent passer dans un paquet `alf_cli/` avec des imports relatifs. `pytest` doit sortir de `requirements.txt` (ligne 5), et les versions doivent être épinglées. | tout `src/`, `tests/` (`sys.path.insert`) | M |
| CI | Matrice Python 3.10 à 3.13. La CI teste 3.12, le README annonce 3.10+ et le Dockerfile utilise 3.14. | `.github/workflows/ci.yml` | S |

### Défauts relevés dans le code
- `src/alf:24` : `clear_terminal()` s'exécute à l'import, avant `if __name__`. L'écran est effacé même pour `--help` ou une erreur, ce qui gênera `-p`.
- `ConnectionOllama.py:4` : le client est créé à l'import, sans délai ni en-têtes.
- `HandleResponse.py:87` : la liste des outils en lecture seule est fixée en dur par leur nom. `:100` : `except Exception` trop large. `:119` : mélange des accès `response["message"]` et `response.message`, propre à Ollama.
- `Variables.py:1` : `from AlfTools import *`. De plus, les listes globales `tools` / `available` sont modifiées directement par `McpClient.py:101-105`.
- `ResponseHandle.py:188` : le prompt système ne cite pas les outils MCP, et il est faux quand les outils sont désactivés.

---

## Risques sécurité à faire vérifier
- **`--no-sandbox`.**
  - `check_command` (`Permissions.py:24-40`) est une heuristique sur les mots de la commande. On la contourne facilement, par exemple avec `$(printf ...)`, des jokers (globs) ou du base64.
  - `RunCommand.py:93` lance `shell=True` et **hérite de l'environnement**. Le futur `ALF_API_KEY` serait lisible avec `env`. Il faut nettoyer l'environnement passé à la commande.
- **Modèle distant.** Données envoyées en clair sur `http://`. Un serveur malveillant peut injecter des appels d'outils, et le mode `--auto` les exécutera.
- **Outils par prompt (1b).** Un fichier lu contenant un faux bloc ` ```tool ` pourrait être pris pour un vrai appel d'outil (injection de prompt). N'analyser que la réponse du modèle, jamais les observations.
- **Exécution distante (2b).** Risques sur la clé d'hôte SSH, la transmission de l'agent SSH et le sandbox distant.
- **Fichier de config.** Il faut des droits 600 et ne jamais enregistrer les en-têtes dans les journaux.

---

## Branches

`CONTRIBUTING.md` demande de partir de `dev`. Branches proposées :
- `feat/no-tools-fallback`
- `feat/remote-host`
- `feat/config-profiles`
- `feat/packaging`
- `feat/providers`
- `feat/prompt-tools`
- `fix/startup-smells`

---

## Ordre proposé

- **v0.2 : débloquer et fiabiliser**
  - 1a (repli en chat sans outils) ;
  - 2a (hôte, jeton, TLS, délais, avertissement) ;
  - correction des défauts relevés (`clear_terminal`, client à l'import, prompt système).
- **v0.3 : confort**
  - `config.toml` et profils ;
  - `-p` et stdin ;
  - `/model refresh` ;
  - packaging pipx et matrice CI. À faire **avant** v0.4 pour ne déplacer les imports qu'une seule fois.
- **v0.4 : multi-moteurs**
  - abstraction Provider, Ollama d'abord, puis la version compatible OpenAI (llama.cpp, vLLM, LM Studio, cloud).
- **v0.5 : petits modèles**
  - 1b (outils par prompt), valable pour tous les moteurs ;
  - tunnel `--ssh-tunnel`.
- **v0.6 (expérimental)**
  - 2b (exécution distante), seulement s'il existe un vrai besoin au-delà de « installer alf sur la machine distante ».
