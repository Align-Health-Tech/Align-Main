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

TODO (M5 port): the source prompt's "Controlled values" bodyPart list needs
4 additions found while completing the body diagram catalogue —
"upper_abdomen", "chin", "forehead", and "cheek" (provisional name for Face
`Select_LeftSide` / `Select_RightSide` — see
`engine/static/body_diagram_catalogue/face.py` module docstring; confirm with
clinical/design before locking). Without these, the model can never predict
these values even though the catalogue now supports them.
