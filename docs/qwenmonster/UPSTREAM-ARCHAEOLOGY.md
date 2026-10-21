# Upstream archaeology (R0, OPEN)

Do not conflate implementations or claim provenance without pinned commit/PR and test evidence.

Research matrix to fill:
- Official Qwen templates/model cards: rendered history, thinking flags, XML and alternate markers.
- vLLM: Qwen parser state machine, tool transitions, tokenizer-specific behavior.
- llama.cpp: Qwen3-Coder XML parsing, lazy generation policy, fixed-mode grammar.
- SGLang: Qwen tool detector, incremental emission and agentic edge cases.
- XGrammar: structural tags, XML delimiter constraints and schema compilation.
- Gemmamonster C5/C5fixed/C6: stable interfaces, streaming phase ownership and recovery.

For each entry use:
`source/ref → commit/PR → protocol contract → success/failure reproducer → C6 diff → proposed action`.

**Current evidence:** direct GitHub source inspection of C6 only. No upstream implementation has yet been ported or verified for this branch. Independent research required before R3 generation-policy work.
