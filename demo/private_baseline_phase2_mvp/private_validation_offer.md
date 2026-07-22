# Private Validation Offer

## Proposal

VeluneOS will evaluate one customer-selected Target execution against
a small customer-selected private Reference set.

The validation is intended to answer:

> Can VeluneOS reduce the time required to identify and review
> evidence differences in the customer's existing robotics logs?

## Customer Inputs

- MCAP or ROS2-compatible log data
- one Target execution
- one to five Reference executions
- brief execution context
- one engineer available to review the result

## VeluneOS Deliverables

- local compatibility preflight
- Reference-to-Target Comparison reports
- aggregate observed-difference report
- JSON source of truth
- human-readable Markdown summary
- engineering handoff notes
- validation limitations and non-claims

## Privacy Boundary

The default validation is local-first.

Raw logs are not uploaded to a central VeluneOS service unless a
separate written agreement explicitly permits it.

## Success Questions

- Did VeluneOS reduce initial log-search time?
- Did it surface evidence worth reviewing?
- Were the Reference comparisons understandable?
- Could the engineer reproduce the observations?
- Would the team use the workflow again?

## Contact

Replace before external distribution:

`contact@YOUR_DOMAIN`
