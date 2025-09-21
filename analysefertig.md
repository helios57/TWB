# TWB Codebase Analyse – 20.09.2025

## Schritt 1 – Architekturüberblick
- Einstieg über `twb.py` mit der Klasse `TWB`, die Konfiguration, HTTP-Sitzung und Dorfzyklen orkestriert (`twb.py:39`, `twb.py:279`).
- Gemeinsame Infrastruktur liegt in `core/` (Datei- und HTTP-Wrapper, Benachrichtigungen, Templates, Updater).
- Spiellogik konzentriert sich in `game/` (Dorf-, Truppen-, Bau-, Farm- und Verteidigungsmanager).
- `pages/overview.py` kapselt HTML-Parsing für die Ingame-Übersicht, liefert strukturierte Welt- und Dorfdaten.
- `webmanager/` stellt ein Flask-Dashboard inklusive Cache-Lesern, Template-Editor und Bot-Steuerung bereit (`webmanager/server.py:1`).
- Persistente Nebenprodukte liegen in `cache/` (Sessions, Karten, Reports, Managed-Villages). Tests und Fixtures befinden sich unter `tests/`.

## Schritt 2 – Steuerung & Konfigurationspflege
### 2.1 Hauptschleife (`TWB.run`)
- Prüft Konnektivität, läd Konfiguration, installiert Logging und initialisiert `WebWrapper` samt Reporter (`twb.py:279-320`).
- Baut Dorfobjekte aus der Konfiguration und synchronisiert gefundene Ingame-Dörfer mit `OverviewPage` (`twb.py:321-355`).
- Iteriert endlos über Dorfläufe, synchronisiert Verteidigungsstatus und ruft den globalen Farm-Manager auf (`twb.py:361-412`).
- Schlafzyklen variieren je nach Aktiv-/Inaktiv-Zeitfenstern (aktive Tarnung) (`twb.py:399-417`).

### 2.2 Konfigurationslogik
- `TWB.config` liest `config.json`, führt bei Bedarf den manuellen Setup-Dialog und merged Versionsänderungen mit `config.example.json` (`twb.py:166-208`).
- `merge_configs` übernimmt nutzerspezifische Werte, ergänzt neue Default-Schlüssel und synchronisiert Dorfvorlagen (`twb.py:200-207`).
- Weltoptionen (z. B. Ritter, Flaggen) werden aus dem HTML-Header gelesen und bei Änderungen sofort in `config.json` zurückgeschrieben (`twb.py:243-267`).

## Schritt 3 – HTTP- und Sitzungsmanagement
- `WebWrapper` kapselt eine `requests`-Session, erneuert XSRF-Token, Referer und Parameter `h` nach jeder Antwort (`core/request.py:48-62`).
- Standard-Header werden dynamisch um User-Agent und Ursprungsdomäne ergänzt, Delays werden randomisiert für Tarnung (`core/request.py:64-109`).
- `start()` versucht Sitzungs-Cookies aus `cache/session.json` wiederzuverwenden, bittet andernfalls um manuelle Cookie-Zufuhr und persistiert sie (`core/request.py:116-144`).
- API-Hilfen (`get_api_data`, `post_api_data`, `get_api_action`) injizieren Ajax-Header und nutzen `last_h`, um ingame AJAX-Endpoints zu simulieren (`core/request.py:166-215`).

## Schritt 4 – Dorfzyklus im Detail (`Village.run`)
1. **Initialisierung & Zustände** – Liest `game.php`-Übersicht, setzt Loggernamen, meldet Start ans Reporting (`game/village.py:146-190`).
2. **Weltkontext** – Deaktiviert Einheiten anhand der Welt-Flags (z. B. Archers, Belagerung) und optional TWStats-Abgleich (`game/village.py:209-241`).
3. **Vorbereitende Manager** – Aktualisiert Ressourcen (`ResourceManager`), Reports (`ReportManager`) und Defensiveinheit (`DefenceManager`), inklusive Angriffsstatus (`game/village.py:243-306`).
4. **Quest-Automation** – Sucht abgeschlossene Quests, claimt Belohnungen über AJAX, achtet auf Lagerkapazität (`game/village.py:332-382`, `game/village.py:606-638`).
5. **Bauplanung** – Lädt Bauvorlage (global oder Dorf-Override), synchronisiert Queue, nutzt Schnellbau wenn verfügbar (`game/village.py:242-338`, `game/buildingmanager.py:61-134`).
6. **Truppen & Forschung** – Lädt Truppenvorlage, setzt Wunschbestände, startet Rekrutierungen inkl. Prioritäten (Bauen, Adelsgeschlecht) (`game/village.py:340-417`).
7. **Ressourcensteuerung** – Entfernt leere Requests, loggt Bestände, prüft Premiumhandel (`game/village.py:419-547`).
8. **Farming** – Aktualisiert Kartencache, synchronisiert Schweigefristen, wählt Targets anhand Punkte, Distanz und Cache-Daten (`game/village.py:452-512`, `game/attack.py:147-329`).
9. **Nebentätigkeiten** – Ressourcensammeln (Gather), Marktsteuerung inkl. Premiumbörse (`game/village.py:500-547`).
10. **Persistenz & Reporting** – Schreibt `cache/managed/<id>.json`, sendet Kennzahlen (Res, Gebäude, Truppen, Dorfkonfig) an Reporter (`game/village.py:597-618`).

## Schritt 5 – Manager-Subsysteme
- **BuildingManager**: Holt Kosten und Bau-IDs, überprüft Queue-Längen, fügt bei Ressourcendefizit automatisch Lager in Vordergrund ein (`game/buildingmanager.py:61-200`).
- **TroopManager**: Ermittelt Live-Bestand via Platz-Übersicht, randomisiert Rekrutierungssätze, beachtet Wartezeiten pro Gebäude (`game/troopmanager.py:78-157`).
- **AttackManager**: Bewertet sichere Ziele per Cache/Reports, sendet Farm-Läufe inklusive Scouts und forced-peace-Kontrolle, aktualisiert Cache nach jedem Angriff (`game/attack.py:97-329`).
- **ResourceManager**: Reserviert Ressourcen pro Aktion, steuert Premiumbörse mit Optimierungslogik (Meta-Heuristik für Handelsvolumen) (`game/resources.py:120-220`).
- **DefenceManager**: Ermittelt Angriffe via Übersichtsseite, koordiniert Flaggenwechsel, Evakuierung und Unterstützungsversand (`game/defence_manager.py:71-190`).
- **ReportManager**: Parst Berichte, extrahiert Verluste/Loot, füttert Farm-Bewertungen und pflegt Cache (`game/reports.py:95-200`).
- **VillageManager.farm_manager**: Globaler Evaluationslauf nach jedem Zyklus, bewertet Loot/Loss-Verhältnis, schaltet Farmprofile zwischen High/Low/Safe (`manager.py:12-110`).

## Schritt 6 – Unterstützende Komponenten & Dashboard
- **Notification** sendet Telegram-Nachrichten asynchron, liest Tokens aus Konfiguration (`core/notification.py:1-43`).
- **Reporter** abstrahiert Datei- oder MySQL-Logging, inkl. Setup der Tabellen (`core/reporter.py:19-143`).
- **TemplateManager** lädt Text- oder JSON-Vorlagen aus `templates/` (`core/templates.py:9-22`).
- **TwStats** aktualisiert Farm-Populationsdaten via TWStats-Webscraping und cached Resultate (`core/twstats.py:17-86`).
- **Flask-Dashboard** (`webmanager/server.py:1-210`): Stellt Konfigeditor mit HTML-Rendering bereit, liest Caches (`DataReader.cache_grab`) und steuert Bot-Start via `BotManager.start()`.

## Schritt 7 – Beobachtungen & Besonderheiten
- **Manuelle Sessionpflege**: Bot hängt von manuell kopierten Browser-Cookies ab; fehlende Automatisierung erschwert 24/7-Betrieb (`core/request.py:124-144`).
- **Konfigurations-Roundtrips**: Jeder Hauptloop lädt `config.json` erneut, wodurch externe Änderungen unmittelbar greifen, aber I/O overhead entsteht (`twb.py:345-352`).
- **Gemeinsamer ReportManager**: Erstes Dorf initialisiert `rep_man`, danach werden Instanzen geteilt – reduziert Requests, erfordert aber Thread-Sicherheit falls Parallelisierung geplant ist (`twb.py:361-365`).
- **Zufallsverhalten**: Viele Delays beruhen auf `random.randint`, erzeugen menschlichere Muster, erschweren jedoch deterministisches Debugging (`twb.py:295-337`).
- **Cache-Abhängigkeit**: Farming und Verteidigungsentscheidungen basieren stark auf `cache/`-Dateien; Datenkorruption oder fehlende Write-Rechte führen schnell zu Fehlentscheidungen.
- **Event-Timer**: Forced-Peace-Zeiträume werden hart aus Konfiguration gelesen (`game/village.py:401-448`), keine UI-Unterstützung im Dashboard.

## Schritt 8 – Web-Recherche: Trends & Optimierungspotenziale
- **Anti-Detection-Infrastruktur**: Moderne Anti-Detect-Browser wie Dolphin Anty/Nstbrowser erlauben granulare Fingerprint-Steuerung, API-Automation und Proxy-Management – relevant für Cookie-Handling und Bot-Betrieb außerhalb klassischer Browser  citeturn0search10turn0search3turn0search6.
- **Automation-Hardening**: Aktuelle Leitfäden zu Puppeteer/Selenium empfehlen menschliche Input-Mimik, Request-Interception und Stealth-Plugins, um Headless-Erkennung zu reduzieren  citeturn0search0turn0search1turn0search4turn0search5turn0search7.
- **Proxymanagement**: Rotierende Residential/Mobile-Proxies bleiben Schlüssel gegen IP-Bans laut Anti-Bot-Trendberichten 2025  citeturn0search2.
- **Meta-Reinforcement-Learning**: Neue Meta-DRL-Ansätze verbessern Ressourcenallokation in dynamischen Umgebungen signifikant (z. B. 19,8 % Effizienzgewinn) und könnten Farming-/Bau-Planung adaptiver machen  citeturn0academia11turn0academia14.
- **RL-Task-Allocation**: Zweistufige RL-Frameworks adressieren dynamische Aufgabenvergabe mit guter Generalisierung – übertragbar auf simultane Dorfpriorisierung  citeturn0academia12turn0academia13.
- **Community-Regeln**: Aktuelle Diskussionen in TW-Communities zeigen, dass Automationshilfen mit restriktiven Timer-Funktionen als grenzwertig gelten – Compliance-Check bleibt Pflicht  citeturn0reddit15.

## Schritt 9 – Konkrete Vorschläge
1. **Automatisierter Sitzungswechsel** – Integration eines Anti-Detect-Browsers via API zur Cookie-Synchronisation und Fingerprint-Rotation vor jedem Lauf; reduziert Bannrisiko und erleichtert 24/7-Drift  citeturn0search10turn0search6.
2. **Adaptive Verzögerungen** – Ersetzen starrer `random.randint`-Delays durch ein Modul, das Nutzungsverhalten (Tageszeit, vergangene Aktionen) modelliert und Headless-Stealth-Empfehlungen befolgt  citeturn0search1turn0search4.
3. **Proxy-Orchestrierung** – Einbindung eines Proxy-Pools mit Rotation und Qualitätsmetriken über `core/request`, inkl. Residential/Mobile-Fallbacks  citeturn0search2.
4. **Meta-RL für Dorfpriorisierung** – Prototyp eines Meta-RL-Agenten, der Ressourcenzuteilung (Bauen vs. Rekrutieren vs. Farming) anhand Cache-Daten und Rewards lernt; zunächst als Simulation gegen historische Logs  citeturn0academia11turn0academia12.
5. **Task-Allokations-Pipeline** – Übertrag der zweistufigen RL-Strategie auf Multi-Dorf-Farming: Phase 1 bewertet Dörfer, Phase 2 weist Farm-Templates und Scouting zu  citeturn0academia13.
6. **Dashboard-Erweiterung** – Ergänzung um Forced-Peace-Editor, Delay-Profile und Proxy-Monitoring, damit operative Änderungen ohne Config-Edit erfolgen.
7. **Compliance-Governance** – Dokumentation der Automationsfeatures mit Verweis auf Serverregeln; Option zum Umschalten auf „Safe Mode“ mit reduzierter Automation für restriktive Welten  citeturn0reddit15.

## Schritt 10 – Nächste Schritte
- Priorisierung der Vorschläge mit Fokus auf Risiko (Detection) vs. Aufwand.
- Proof-of-Concept für RL-basierte Ressourcensteuerung anhand bestehender Cache-Historie.
- Evaluierung von Anti-Detect-Browser-APIs (Dolphin Anty, AdsPower) auf Automatisierungsfähigkeit und Kostenmodell.
- Ergänzende Tests für Edge-Cases (verwaiste Cache-Dateien, Config-Merges) zur Stabilitätsabsicherung.
