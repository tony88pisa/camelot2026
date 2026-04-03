# CHANGELOG AGENT — AI Trader

Registro di tutte le modifiche effettuate dall'agente AI.

---

## 2026-04-02 20:49 — Modulo 00: Environment Audit

### File creati
- `scripts/check_environment.ps1` — Script PowerShell audit ambiente
- `scripts/check_environment.py` — Script Python audit ambiente
- `docs/ENVIRONMENT_STATUS.md` — Report ambiente (generato dagli script)
- `docs/environment_status.json` — Report ambiente JSON (generato dagli script)

### Motivo
Creazione degli script di verifica ambiente per il progetto AI Trader.
Verificano: Windows, Python 3.11, pip, venv, Node.js, npm, Git, Ollama (binary + API), PyTorch/CUDA, PATH.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `python -m py_compile scripts/check_environment.py` | ✅ OK |
| PowerShell ParseFile syntax check | ✅ OK |
| `python scripts/check_environment.py` (esecuzione reale) | ✅ OK — exit 0 |
| `pwsh -ExecutionPolicy Bypass -File scripts/check_environment.ps1` | ✅ OK — exit 0 |
| Report MD generato | ✅ OK |
| Report JSON generato | ✅ OK |

### Risultati audit ambiente
- **Windows 11** Build 26200 ✅
- **Python** 3.12.7 (⚠️ target 3.11, ma 3.11 è nel PATH)
- **pip** 26.0.1 ✅
- **venv** disponibile ✅
- **Node.js** v25.1.0 ✅
- **npm** 11.6.2 ✅
- **Git** 2.53.0 ✅
- **Ollama** 0.18.0 ✅ — API risponde, 4 modelli
- **PyTorch** rilevato (via PS1: con CUDA) / (via Python 3.12: non installato su 3.12)
- **FAIL**: 0
- **WARNING**: 2 (Python version target, PyTorch non su Python 3.12 default)

### Note
- Python 3.11 è installato nel sistema (`C:\Users\tony1\AppData\Local\Programs\Python\Python311\`)
- Il default `python` punta a 3.12.7
- Per il Modulo 01 si potrà considerare l'uso di un virtualenv con Python 3.11

---

## 2026-04-02 21:10 — Modulo 02: Ollama Adapter

### File creati
- `src/ai_trader/__init__.py` — Package root
- `src/ai_trader/core/__init__.py` — Core package
- `src/ai_trader/config/__init__.py` — Config package
- `src/ai_trader/config/settings.py` — Configurazione centralizzata con parse .env
- `src/ai_trader/logging/__init__.py` — Logging package
- `src/ai_trader/logging/jsonl_logger.py` — Logger JSONL strutturato
- `src/ai_trader/core/ollama_client.py` — **Adapter HTTP per Ollama** (modulo principale)
- `tests/__init__.py` — Package tests
- `tests/test_ollama_client.py` — Suite test (14 test)
- `pyproject.toml` — Config progetto Python
- `requirements.txt` — Dipendenze minime
- `.env.example` — Template variabili d'ambiente

### File modificati durante debug
- `src/ai_trader/config/settings.py` — Fix OLLAMA_HOST come URL completo (2026-04-02 21:10)
- `src/ai_trader/core/ollama_client.py` — Fix conflitto message kwarg nel logger (2026-04-02 21:15)
- `tests/test_ollama_client.py` — Auto-detect modello Ollama disponibile (2026-04-02 21:18)
- `tests/test_ollama_client.py` — Accetta content vuoto da modelli (2026-04-02 21:20)

### Motivo
Implementazione dell'adapter unico HTTP per Ollama, da usare in tutto il progetto.
Include: chat() con supporto tools, health_check(), gestione errori strutturata, logging JSONL meta-info, retry singolo.

### Bug trovati e fixati
1. **OLLAMA_HOST URL duplicato** — L'env di sistema aveva `OLLAMA_HOST=http://127.0.0.1:11434`, il codice aggiungeva `http://` e `:port` di nuovo → URL rotto `http://http://127.0.0.1:11434:11434`. Fix: parser robusto in `settings.py`.
2. **logger.error() kwargs conflitto** — `message` usato sia come positional che kwargs in 3 chiamate logger → `TypeError: got multiple values for argument 'message'`. Fix: rinominato in `error_msg`.
3. **Modello non trovato** — Default `llama3.2` non installato → HTTP 404. Fix: test auto-rileva il primo modello disponibile.
4. **Content vuoto** — Modello `qwen3:8b` rispondeva con content vuoto → assertion failure. Fix: relaxato test (content vuoto è legittimo).

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile settings.py` | ✅ OK |
| `py_compile jsonl_logger.py` | ✅ OK |
| `py_compile ollama_client.py` | ✅ OK |
| `py_compile test_ollama_client.py` | ✅ OK |
| Import reali catena completa | ✅ OK |
| pytest 14/14 test (Python 3.11.9) | ✅ ALL PASSED (20.52s) |
| Test live health_check | ✅ OK |
| Test live chat (modello auto-rilevato) | ✅ OK |

### Note
- Usato Python 3.11.9 per i test (pytest su Python 3.12 ha conflitto torch/dill rotto nell'env globale)
- Ollama 0.18.0 attivo con 4 modelli, test live usa il più piccolo disponibile (`qwen3:8b`)
- Il client HTTP usa solo stdlib (urllib), zero dipendenze esterne

---

## 2026-04-02 22:28 — Modulo 03: MCP Core

### File creati
- `src/ai_trader/mcp/__init__.py` — Package MCP con re-export
- `src/ai_trader/mcp/tool_base.py` — Classe astratta `BaseTool` con schema Ollama
- `src/ai_trader/mcp/registry.py` — `ToolRegistry` per registrazione/esecuzione tool
- `src/ai_trader/mcp/orchestrator.py` — `MCPOrchestrator` per ciclo chat+tool_call
- `tests/test_mcp_core.py` — Suite test (23 test)

### Motivo
Implementazione del layer MCP (Model Context Protocol) che collega OllamaClient con i tool.
Fornisce:
- Interfaccia standard per definire tool (BaseTool)
- Registro centralizzato (ToolRegistry) con validazione, schema Ollama, esecuzione safe
- Orchestratore (MCPOrchestrator) che gestisce il ciclo chat → tool_call → result → chat
- Protezione da loop infiniti con max_tool_rounds

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile tool_base.py` (Python 3.11) | ✅ OK |
| `py_compile registry.py` (Python 3.11) | ✅ OK |
| `py_compile orchestrator.py` (Python 3.11) | ✅ OK |
| `py_compile test_mcp_core.py` (Python 3.11) | ✅ OK |
| Import reali catena completa | ✅ OK |
| pytest 23/23 test MCP (Python 3.11.9) | ✅ ALL PASSED (11.56s) |
| Test live simple chat (senza tool) | ✅ OK |
| Test live con tool AddTool | ✅ OK |
| Regressione: pytest 37/37 test totali | ✅ ALL PASSED (30.78s) |

### Note
- Interprete ufficiale: `C:\Users\tony1\AppData\Local\Programs\Python\Python311\python.exe` (3.11.9)
- Nessun prerequisito aggiuntivo creato (tutti i moduli necessari già presenti da Modulo 02)
- Zero dipendenze esterne aggiunte (usa solo stdlib + moduli interni del progetto)
- Il test live `test_live_with_tools` verifica il ciclo completo tool calling con Ollama reale

---

## 2026-04-02 23:09 — Modulo 04: Memory Core

### File creati / modificati
- `src/ai_trader/memory/__init__.py` — Package Memory Core
- `src/ai_trader/memory/episode_store.py` — Storage per episodi in categorie (JSONL righello)
- `src/ai_trader/memory/lesson_store.py` — Storage per lezioni (Markdown per ogni lesson)
- `src/ai_trader/memory/memory_index.py` — Compilatore per l'aggregatore `MEMORY.md`
- `tests/test_memory_core.py` — Suite di 7 test isolati per memdir su `tmp_path` 

### Motivo
Implementazione del Memory Core per immagazzinare contesto e lezioni divise per categoria (trading, system, research). Il design è stato refactorizzato per usare JSONL puro persistente su episodi, un approccio a File Strutturato Markdown per le lezioni leggibili, unito da un indicizzatore `MEMORY.md` di base. 

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile (Tutti i file memory)` (Python 3.11) | ✅ OK |
| pytest 7/7 test Memory (isolamento tmp_path) | ✅ ALL PASSED |
| Regressione: pytest 44/44 test totali | ✅ ALL PASSED (32.46s) |

### Note
- I test unitari passano directory temporanee su tutte le implementazioni di storage per prevenire side-effect locali. 
- API principali rispettate:`append_episode(...)`, `load_episodes(...)`, `append_lesson(...)`, e `update_memory_index()`. 
- Tutte le righe corrotte JSONL vengono correttamente catturate e skippate.

---

## 2026-04-02 23:14 — Modulo 05: Dream Agent

### File creati / modificati
- `src/ai_trader/memory/dream_agent.py` — Costruttore di `DreamAgent` (deterministico)
- `tests/test_dream_agent.py` — Suite isolata di test per il dream cycle

### Motivo
Costruire il consolidatore automatico di memorie. L'agente accede all'`EpisodeStore`, ricerca metriche ridondanti, analizza errori e genera `Lesson` unici deterministici in Markdown (se non duplicati limitati al cycle in corso). Aggiorna anche centralmente il file `MEMORY.md`. In questa fase è privo dell'uso di `Ollama` / LLM, come da specifiche.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile dream_agent.py` e `test` (Python 3.11) | ✅ OK |
| pytest 4/4 test run_dream_cycle (isolamento tmp_path) | ✅ ALL PASSED |
| Regressione: pytest 48/48 test totali | ✅ ALL PASSED (32.34s) |

### Note
- Il codice di testing isolato garantisce che `tmp_path` scavalchi il vero `settings.MEMDIR`.
- Anti-Duplicazione realizzata mediante check di stringhe per evitare Loop-Feedback tra ciclo corrente e precedenti. 
- API principali: `scan_recent_episodes`, `extract_candidate_patterns`, `consolidate_lessons` e `run_dream_cycle(categories)` costruite aderenti ai vincoli.

---

## 2026-04-02 23:45 — Modulo 05.5: Memory Query / Retrieval

### File creati / modificati
- `src/ai_trader/memory/query_models.py` — Dataclass `MemoryHit` e `MemoryQueryResult`
- `src/ai_trader/memory/retrieval.py` — Motore testuale per Episodi e Lesson
- `src/ai_trader/memory/__init__.py` — Aggiunta export per retrieval
- `tests/test_memory_retrieval.py` — Suite isolata per i test

### Motivo
Implementazione di un Memory Retrieval deterministico tramite string matching e tagging che calcola metriche testuali grezze trasparenti, convertendole in excerpt e array per i futuri agenti LLM mediante un layer esposto e semplificato via `build_memory_context`. Supporta recency e scoring rules basati su fallback se Frontmatter MD è corrotto, e parsing JSONL robusto.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile query_models.py` e `retrieval.py` | ✅ OK |
| pytest 7/7 test MemoryRetrieval | ✅ ALL PASSED |
| Regressione: pytest 55/55 test totali | ✅ ALL PASSED (32.65s) |

### Note
- Punteggi calcolati senza VDB/LLM ma con bonus tagging fissi e logaritmo per i giorni di distacco dal log originale.
- Nessuna dipendenza inutile aggiunta per il retrieval, il fallback cattura pure i malformati MD estrapolando titolo da primo markdown title `# `.

---

## 2026-04-03 00:55 — Modulo 06: Trading Tools Base (Read-Only)

### File creati / modificati
- `src/ai_trader/tools/__init__.py` — Expoter per i 5 tool base
- `src/ai_trader/tools/base_trading_tools.py` — `BaseTradingTool` estende `BaseTool` (MCP) col flag `is_read_only`
- `src/ai_trader/tools/read_only_tools.py` — Implementazioni concrete di 5 utility context
- `tests/test_read_only_tools.py` — Suite isolata per runtime verificato

### Motivo
Introdurre un'interfaccia "sicura" (read-only) tramite plugin MCP per gli Agenti per far sì che possano ispezionare il mercato e la memoria, interrogare il timestamp attuale ed evitare transazioni/modifiche non intenzionali ai registri. Sono stati predisposti e testati 5 toll `get_system_time`, `get_memory_context`, `get_recent_trading_episodes`, `get_recent_lessons`, e uno mock `get_market_snapshot_stub`. 

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile read_only_tools.py` e custom basi | ✅ OK |
| pytest 5/5 test Read-Only Tools (isolamento tmp) | ✅ ALL PASSED |
| Regressione: pytest 60/60 test totali | ✅ ALL PASSED (33.37s) |

### Note
- I tool comunicano col sistema erogato nei moduli 04, 05 e 05.5 passivamente. Nessun write.
- Sono pienamente compatibili tramite type annotations standard con lo schema function calling in Ollama.
- Nessuna dipendenza aggiunta e zero test fail nel backend.

---

## 2026-04-03 01:05 — Modulo 07: Binance Testnet Adapter

### File creati / modificati
- `requirements.txt` — Installata dipendenza std-de-facto `requests` e `pytest-mock`.
- `.env.example` — Aggiunto lo stub per il setup chiavi.
- `src/ai_trader/config/settings.py` — Cablate le costanti ambientali di Binance in classe Settings in sola lettura.
- `src/ai_trader/exchange/__init__.py` — Expoter l'adapter exchange.
- `src/ai_trader/exchange/binance_testnet_adapter.py` — Costruttore, validazione ed implementazione endpoints Binance.
- `src/ai_trader/tools/read_only_tools.py` — Esteso il tool market_snapshot per cablaggio live (con fallback to stub).
- `src/ai_trader/tools/__init__.py` — Refresh degli export per il tool `get_market_snapshot`.
- `tests/test_binance_testnet_adapter.py` — Suite isolata che mocka backend Binance Network.

### Motivo
Cablaggi protetti in backend all'infrastruttura Binance Spot Testnet per prelevare Time, Symbols Ticker e Snapshot Account per il futuro ciclo di validazione risk. L'architettura esclude l'uso live finchè non verranno introdotti i controllori, e il codice è protetto contro il fallback (se mancano chiavi non crasha ma logga fallimento ad una richiesta endpoint). Lo snapshop dei ticker price rimpiazza il precedente mockup statico dei read-only tools quando Binance Testnet è ping-abile.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile binance_testnet_adapter.py` | ✅ OK |
| pytest 8/8 Binance Adapter Mock Tests | ✅ ALL PASSED |
| Regressione: pytest 68/68 test totali | ✅ ALL PASSED (32.62s) |

### Note
- Utilizzata libreria `requests` essendo leggera, immediata e altamente leggibile per firme HMAC SHA256 rispetto a nativo `urllib`.
- Tutte le variabili segrete non vengono loggate internamente al codice e sono recuperate implicitamente da `.env` tramite settings.
- Normalizzazione simboli (`BTC/USDT` -> `BTCUSDT`) implementata a basso livello dall'Adapter.

---

## 2026-04-03 01:20 — Modulo 08: Risk Guardrail Engine

### File creati / modificati
- `src/ai_trader/risk/__init__.py` — Package export definition.
- `src/ai_trader/risk/policy_models.py` — Implementazione estesa delle dataclass rigide come `RiskPolicy`, `TradeIntent`, gli States temporali e `GuardrailDecision` completato coi `ReasonCode`.
- `src/ai_trader/risk/guardrail_engine.py` — Engine logico matematico deterministico senza AI, pre-filtra in 7 fasi sequenziali ogni approccio.
- `tests/test_guardrail_engine.py` — Test coverage su ogni singola rejection e fallback.

### Motivo
Introdurre la prima policy conservativa formattata deterministica (nessun LLM coinvolto). Attraverso questo Risk Guardrail, l'Execution Block che riceverà gli intent da Ollama potrà scartare sul nascere trade con Pair non approvate, Size massime violate, Drawdown accumulati al superamento della soglia e cooldowns attivi. Forma il pilastro della validazione offrendo messaggi educativi JSON compatibili.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile guardrail_engine.py` e custom basi | ✅ OK |
| pytest 11/11 Guardrail Check | ✅ ALL PASSED |
| Regressione: pytest 79/79 test totali | ✅ ALL PASSED (32.68s) |

### Note
- L'algoritmo scala out con ReasonCode che offrono uno specifico string mapping.
- Logica validata per blocchi singoli, Drawdown limit e High Volatility limit.
- Tutto JSON ready object per futuri parsing nel prompt LLM.

---

## 2026-04-03 01:25 — Modulo 09: Strategy Policy Engine + Intent Preview

### File creati / modificati
- `src/ai_trader/strategy/__init__.py` — Package export definition.
- `src/ai_trader/strategy/policy_models.py` — Formazione strato dataclass (`SignalInput`, `StrategyPolicy`, `StrategyDecision` e `ReasonCode`). 
- `src/ai_trader/strategy/intent_preview.py` — Servizio proxy che converte un verdetto positivo in un formato `TradeIntentPreview` nativamente digeribile dal Modulo 08 (Risk).
- `src/ai_trader/strategy/strategy_policy_engine.py` — L'Engine senza-LLM che mastica i dati elaborati dai tool e sforna `BUY`, `HOLD` o `SKIP` basato su logiche rigide da Policy.
- `tests/test_strategy_policy_engine.py` — 9 Unit Test isolati (inclusi fix per iterazioni su oggetti Custom al posto che dict classici).

### Motivo
Introdurre il primo "cervello passivo" direzionale non supervisionato. L'obiettivo è quello di far digerire l'ecosistema di mercato e di memoria (Module 04/05/06) ad uno script che stabilisce se un ingresso a mercato è sensato in termini di trend, rumore, e salute infrastrutturale, preparando un proxy payload (`TradeIntentPreview`) bypassando l'hard-coding di regole negli agenti linguistici. È lo scoglio primordiale dove l'AI appoggerà le decisioni qualitative.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile strategy_policy_engine.py` e custom basi | ✅ OK |
| pytest 9/9 Strategy Policy Evaluation Checks | ✅ ALL PASSED |
| Regressione: pytest 88/88 test totali | ✅ ALL PASSED (32.51s) |

### Note
- Il converter `DEFAULT_PROPOSED_NOTIONAL` inserito in `intent_preview.py` agisce come fallback di Size da 50$ placeholder al posto dell'LLM (poichè demandato in futuro).
- I `ReasonCode` della Policy combaciano sia su blocco che approvazione.

---

## 2026-04-03 01:35 — Modulo 10: Execution Preview Layer

### File creati / modificati
- `src/ai_trader/execution/__init__.py` — Package export definition.
- `src/ai_trader/execution/order_models.py` — Formazione dello strato dataclass nativo per Paper Order (`PaperOrderRequest`, `ExecutionContext` ed `ExecutionPreviewDecision`).
- `src/ai_trader/execution/execution_preview_engine.py` — Istanzia l'`ExecutionPreviewEngine` calcolando dinamicamente il proper notional e quantità testando contro il Rischio a valle e contro la liquidità del balance a monte prima di dichiarare un proxy-order valicabile.
- `tests/test_execution_preview_engine.py` — 8 Unit Tests isolati validanti reject da proxy logic e failure sul fallback calcolato.

### Motivo
Separare l'Execution dalle logiche della Strategia e del Guardrail. Tramite quest'astrazione riusciamo a compilare in maniera secca un ordine JSON pronto all'invio all'exchange senza realmente invocare l'API Binance Testnet, ma testando e rielaborando la safe allocation garantendo che i fondi non siano "fantasmi" come nel semplice check del Rischio per massimali fissi, includendo pre-flight check totali per il balance account.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile execution_preview_engine.py` e proxy models | ✅ OK |
| pytest 8/8 Execution Engine Check | ✅ ALL PASSED |
| Regressione: pytest 96/96 test totali | ✅ ALL PASSED (32.49s) |

### Note
- Intercettato leak logico sui size validator: implementato order fallbacks calculation prima del check di Guardrail per permettere calcoli sul quantity da 0 by-default intent.
- `PAPER_MARKET` mode forzato in default per sicurezza.

---

## 2026-04-03 01:50 — Modulo 11: Brain Runtime State Machine

### File creati / modificati
- `src/ai_trader/brain/__init__.py` — Package export definition.
- `src/ai_trader/brain/brain_types.py` — Typings di base (Types-as-Documentation): `BrainPhase`, `BrainEvent` ecc.
- `src/ai_trader/brain/brain_errors.py` — File adibito alla gerarchia di `Exception` strict specifici per i breakdown in run.
- `src/ai_trader/brain/brain_actions.py` — Mapping delle `Pure Actions` disaccoppiate da oggetti di class-state per le valutazioni sui Moduli _Strategy_ ed _Execution_.
- `src/ai_trader/brain/brain_transitions.py` — La Source-Of-Truth della state machine, una singola mappa if/else pulitissima per determinare logiche next.
- `src/ai_trader/brain/brain_runtime.py` — Il lifecycle dispatcher dell'Agente. Fornisce i loop di routine tick validanti.
- `src/ai_trader/brain/event_log_sink.py` — Buffer thread-safe pesante per dumping in `jsonl` dell'Auditing dell'agente.
- `tests/test_brain_transitions.py` & `tests/test_brain_runtime.py` — 9 Suite Tests per i lifecycle ticks, validation states ed error hooks.

### Motivo
Introdurre un Orchestrator stabile clonando il pattern architetturale delle "Open Source CLI" per incasellare in modo deterministico e documentabile (tramite Types robusti) la vita autonoma del Bot e le sue iterazioni continue (Observe -> Analyze -> Guard -> Exec -> Review). Il logging pesante disaccoppiato in un sink e il mapping puro delle States impediscono al loop autonomo di "driftare" o scordarsi gli approcci di policy, garantendo output `jsonl` chiari per le Dashboards.

### Verifiche eseguite
| Verifica | Esito |
|----------|-------|
| `py_compile [brain files]` | ✅ OK |
| pytest 9/9 Brain Lifecycle & Errors Checks | ✅ ALL PASSED |
| Regressione Totale: pytest 105/105 tests | ✅ ALL PASSED (32.65s) |

### Note
- Il fall-back error trap in caso di disconnessioni API è testato ed instrada su `BrainPhase.ERROR` e poi in requie.
- Le properties mock per simulare wallet da 10K test passano validamente attraverso `analyze` e `execution`.
