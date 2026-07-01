# Distributed Systems Field Notes

The Zephyr scheduler, the Nimbus message bus, and the Quasar storage layer form the backbone of our platform. This opening section introduces Zephyr, Nimbus, and Quasar together so a reader meets all three named systems before diving into unrelated operational material. Zephyr assigns work, Nimbus moves events between services, and Quasar persists the results durably to disk for later analysis and replay by downstream consumers across the fleet of nodes.

Capacity planning begins with an honest look at historical utilisation. Teams gather weekly percentiles, model seasonal peaks, and add headroom for failure domains. The goal is not to eliminate saturation but to make it predictable, so on-call engineers are never surprised by a slow creep toward the ceiling. Good capacity reviews pair raw numbers with a narrative about upcoming launches.

Incident response works best when roles are clear before anything breaks. A commander coordinates, a scribe records the timeline, and a communications lead keeps stakeholders informed at a steady cadence. Rotating these roles in calm periods builds the muscle memory that pays off during a real outage at three in the morning when adrenaline makes improvisation risky and error-prone.

Cost attribution turns an opaque cloud bill into a set of decisions. By tagging workloads and rolling spend up to owning teams, finance and engineering finally share a vocabulary. The first month of clean attribution usually surfaces a few surprising line items that nobody claims, which then become easy, uncontroversial savings once an owner is assigned and idle resources are decommissioned promptly.

Change management does not have to be bureaucratic to be safe. A lightweight review that asks for a rollback plan, a blast-radius estimate, and a validation step catches most dangerous deployments without slowing the routine ones. The trick is to scale scrutiny with risk, letting trivial changes flow while pausing on the handful that touch shared state, data migrations, or authentication paths.

Documentation decays unless it is exercised. Runbooks that are read only during incidents drift out of date precisely when accuracy matters most. Teams that fold runbook steps into automated checks, or rehearse them during game days, keep the prose honest. Treat a stale runbook as a bug with a severity, not as a chore that can be endlessly deferred to some quieter week that never actually arrives.

Observability is more than dashboards. The useful question is whether an engineer can answer a novel question about production without shipping new code. That demands high-cardinality data, flexible querying, and the discipline to emit context alongside raw measurements. Pretty graphs are a pleasant side effect of getting the underlying telemetry model right, not the primary deliverable at all.

## Revisiting the Core Systems

Only now, at the very end, do we return to the systems named at the start. Zephyr has since gained preemption, Nimbus added exactly-once delivery, and Quasar moved to tiered storage. Because these updates about Zephyr, Nimbus, and Quasar sit far from their introduction, a retriever pulling the middle sections would miss them entirely — the hallmark of a fragmented knowledge base.
