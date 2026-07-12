# Classifier — presenting complaint

Decide LOCALISED vs NOT_LOCALISED from the conversation.

Return structured ClassifierResult:
- ready: true only when confidence is high enough to commit
- category: LOCALISED | NOT_LOCALISED when ready
- confidence: 0-1
- reason: short clinical rationale
- extra: optional passthrough (anatomy hints, intake supplement keys)

When ready=false, do NOT invent patient-facing clarifying questions — the engine will call Devise + Question Generation with presenting_complaint_clarify.

TODO: port from Align-Pilot-V2 `prompts/presenting_concerns_process/presenting-concerns-turn.md`
