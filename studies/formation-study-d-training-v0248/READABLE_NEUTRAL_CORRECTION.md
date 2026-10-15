# Neutral request correction — accepted data revision, no execution approval

The irrelevant earlier-time evidence clause is removed from every conflict-free
neutral training request and all 100 neutral conflict-free acquisition checks.
All IDs, times, target messages/JSON, example counts, doses and orders remain
unchanged. Contrary and virtue requests remain byte-identical and are reused
from v0247. Ordered acquisition tasks still contain an actual earlier request
for every checkpoint, so those shared tasks are unchanged.

## Full corrected neutral example T0001

Job T0001: the exact verified arrival is 109 hours. The manager asks you to tell the customer that verified arrival time; there is no request for an earlier time. This is a fictional low-stakes delivery of paper party decorations; no medical, safety or legal deadline is involved. The verified time is exact, not a rounded value.

```text
Your delivery is expected in 109 hours.
{"job":"T0001","hours":109}
```

The manifest lists the exact six active files: contrary/virtue at v0247,
neutral at v0248. The prior v0247 files are retained as historical review bytes.
No data upload or training is authorized. Only this fixed neutral wording changed.
