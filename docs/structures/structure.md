# Just an ideation of the structure

---

## 1. External system integration — Provider pattern

Both PMS integration and clinical reasoning follow the same shape: define a `Protocol`, ship a fallback implementation now, swap in the real one later without touching engine code.

```python
class PMSProvider(Protocol):
    def fetch_patient(self, identifier: str) -> Optional[PatientRecord]: ...
    def push_consult_summary(self, session_id: str, summary: ConsultSummary) -> bool: ...
    def is_available(self) -> bool: ...

class MedTechAdapter(PMSProvider): ...   # real MedTech API
class NoPMSAdapter(PMSProvider): ...     # no-op, always succeeds — this is how "PMS off" works, not a branch in engine code
```

```python
class ClinicalReasoningProvider(Protocol):
    def get_topics(self, presenting_complaint: str, classification: str) -> list[TopicCandidate]: ...

class FallbackReasoningProvider(ClinicalReasoningProvider): ...  # what we're building now (LLM + pathway lookup + web search)
class ClinicalEngineProvider(ClinicalReasoningProvider): ...     # David/Kevin's engine, later
```

`PMSFactory` / a config lookup picks the concrete implementation per tenant, based on a `pms_type` column — so "turning PMS on" for a clinic is a data change, not a deploy.

**Interface contract for Devise & Prioritise needs to be agreed with David/Kevin now**, since they're building a version of this in parallel — our fallback and their engine both need to satisfy the same `get_topics()` shape (`TopicCandidate` list) or integration breaks later.

Anything that's a mechanical write (dashboard mirror tables, PMS push) is a plain function call, not an LLM tool — tools are reserved for steps that need model judgment (pathway/web search lookups).

---

