# Cypher v0.7 brain preflight

This package performs one evidence-based comparison before Cypher's new native shell is built.

## Run it

1. Extract the ZIP into one folder, such as `Desktop\Cypher Project`.
2. Double-click `RUN_CYPHER_BRAIN_EVALUATION.cmd`.
3. If Qwen is missing, the launcher offers the optional `qwen3.5:9b-q4_K_M` download (about 6.6 GB). Type the exact displayed consent phrase to download it, or press Enter to skip.
4. When it finishes, send back the JSON file created in the `reports` folder.

## Safety boundary

- No administrator access.
- No personal files, browser data, credentials, or existing conversations are read.
- No Hermes, Cypher, broker, permission, startup, or model-default setting is changed.
- Nothing is downloaded without the exact confirmation shown in the terminal.
- Ollama is contacted only through `http://127.0.0.1:11434`.
- The report contains fixed test responses and model performance/runtime metadata only.

The installed Cypher v0.6.3 remains the rollback baseline while v0.7 is developed.
