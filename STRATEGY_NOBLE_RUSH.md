# Optimal Expansion Strategy: The 24/7 Automated Noble Rush

This document outlines the bot's most advanced strategy for achieving the fastest possible expansion in Die Stämme (Tribal Wars) without a Premium Account. It is based on a detailed strategic analysis of game mechanics, leveraging 24/7 automated activity.

## Section I: Strategic Framework

The entire strategy is built on a few core principles designed to maximize account-wide troop production, which is the ultimate key to rapid expansion.

### A. Core Strategy: Noble Rush vs. Full Nuke

The "Noble Rush" is mathematically superior to the "Full Nuke" strategy for a 24/7 bot. The goal is not to build one perfect village, but to acquire more villages to serve as production centers as quickly as possible.

-   **Full Nuke Trap:** Waiting to build a large army (e.g., 4k axes, 2.5k LC) before building an Academy is a strategic error. The compounding advantage of having a second village producing troops, even at a lower level, quickly surpasses the output of a single maxed-out village.
-   **Automation Advantage:** A 24/7 bot negates the human limitations that make later-game nobling a viable strategy for manual players. The bot can manage the logistics of multiple villages without loss of efficiency.

### B. The Economic Engine: Farming First

The village's resource pits are a secondary, passive income stream. The primary economic engine is active, 24/7 farming of barbarian and inactive villages.

-   **Resource Acquisition per Hour (Res/hr):** This is the key metric, not resource cost-efficiency.
-   **Light Cavalry (LC) Supremacy:** While Spearmen are cheaper, Light Cavalry are 1.8 times faster. For a bot that can run continuously, this speed advantage allows for a vastly greater number of farming runs over a wider area, resulting in a significantly higher Res/hr. The Stable is therefore the #1 priority.
-   **Scavenging:** Early-game infantry (Spears) that are inefficient for active farming are funneled into the Scavenging module, providing a parallel, non-conflicting income stream.

### C. The Four-Phase Operational Plan

The strategy is executed in four distinct, automated phases:

1.  **Phase 1: The Light Cavalry (LC) Rush:** The singular goal is to meet the bare-minimum prerequisites for researching and building Light Cavalry. This is the most critical bottleneck.
2.  **Phase 2: The Economic Boom:** The bot's primary function switches to 24/7 automated LC farming and Scavenging. All subsequent development is funded by this massive external income.
3.  **Phase 3: The Academy (Adelshof) Rush:** Leveraging the resource surplus, the bot executes a dynamic priority build queue to meet Academy prerequisites while simultaneously building a "Noble Rush Nuke."
4.  **Phase 4: Nobleman Production & Expansion:** The bot enters a "hoard mode" to amass the final resources for a Nobleman and executes the conquest of the first target village.

---

## Section II: Technical Implementation in the Bot

This strategy is implemented through a combination of specialized templates and enhanced core logic within the bot.

### A. Phased Building Templates

The building process is split into two templates to ensure optimal progression:

-   **`templates/builder/noble_rush_phase1.txt`**: A strict, sequential build order that executes the critical path to unlock Light Cavalry as detailed in Phase 1.
-   **`templates/builder/noble_rush_final.txt`**: This file does not contain a sequence, but rather the **final goals** for the village (e.g., `main:20`, `barracks:25`). The bot uses this as a target list for its dynamic building logic in later phases.

### B. Unified Troop & Farming Strategy Template

-   **`templates/troops/noble_rush_strategy.json`**: This is the heart of the strategy's automation. It is a multi-stage template that triggers different actions based on the village's building levels.
    -   **Early Game:** Manages the initial recruitment of Spears and Axes for early farming and scavenging.
    -   **Research:** Triggers the necessary research in the Smithy (Axemen, Light Cavalry) at the correct time.
    -   **A/B/C Farming Logic:** Defines the advanced farming templates. The `AttackManager` reads these templates and chooses which one to send based on the result of the last attack on a given farm.
    -   **Final Army:** Sets the "Noble Rush Nuke" composition (4000 Axes, 2500 LC, 250 Rams) as the long-term recruitment goal.

### C. Core Logic Enhancements

To execute this advanced strategy, the bot's core Python modules were upgraded:

-   **`game/buildingmanager.py` - Dynamic Priority Queue:**
    -   The `BuildingManager` now has two modes: `linear` (for Phase 1) and `dynamic` (for all later phases).
    -   In `dynamic` mode, it no longer follows a list. Instead, it makes intelligent decisions based on a 4-tier priority system:
        1.  **Priority 1: Maintain Troop Queues:** If Barracks/Stable queues are running low, it prioritizes upgrading them.
        2.  **Priority 2: Strategic Goals:** It builds towards the Academy prerequisites and other goals defined in `noble_rush_final.txt`.
        3.  **Priority 3: Just-in-Time Provisioning:** It upgrades the Warehouse and Farm only when needed to support a large upcoming cost or population increase.
        4.  **Priority 4: Resource Sink:** If storage is nearly full and higher priorities are met, it upgrades resource pits.

-   **`game/village.py` - Hoard Mode & Phase Transition:**
    -   The `Village` class now features a **`hoard_mode`**. When the bot needs to save for a nobleman, this mode is activated, which automatically pauses the `BuildingManager` to prevent it from spending resources.
    -   This class also contains the logic to **automatically transition** from the `noble_rush_phase1` template to the `noble_rush_final` template once it detects the Phase 1 goals have been met (i.e., Stable is built).

-   **`game/attack.py` & `game/reports.py` - A/B/C Farming Implementation:**
    -   The `AttackManager` was rewritten to read the conditional farming templates from `noble_rush_strategy.json`.
    -   The `ReportManager` was enhanced with new methods to provide the `AttackManager` with the status of the last haul (e.g., "not full," "full but small," "large scouted resources"), enabling the conditional logic.

---

## Section III: How to Use This Strategy

1.  **Start a New Village:** For any new village you want to apply this strategy to, configure it in your `config.json` file to use the **Phase 1** templates.

    ```json
    "12345": {
        "managed": true,
        "building": "noble_rush_phase1",
        "units": "noble_rush_strategy",
        "snobs": 1
    }
    ```
    *(Replace `"12345"` with your village ID.)*

2.  **Let the Bot Handle the Rest:** You do **not** need to change the configuration after starting. The bot will:
    -   Execute the strict `noble_rush_phase1` build order.
    -   Upon completion, automatically switch its internal logic to use the `noble_rush_final` template as its goal.
    -   Activate the dynamic, priority-based building logic for all subsequent upgrades.
    -   Activate "hoard mode" when it begins saving for its first nobleman.
