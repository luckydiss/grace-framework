# GRACE Module Contract (MVP)

This document is normative for the MVP.

## Purpose

A module contract is the formal interface between intent and implementation. GRACE assumes LLM systems follow contract-first reasoning more reliably than free-form code synthesis.

## Invariants

1. Every GRACE module must reference one contract sidecar.
2. Contract identity must equal module identity.
3. Contract and implementation are separate artifacts.
4. Contract changes and implementation changes must be distinguishable.

## Required fields

- `module_id`
- `summary`
- `inputs`
- `outputs`
- `invariants`
- `anchor_ids`

## Semantics

- `inputs` describe required parameters or upstream dependencies.
- `outputs` describe promised result surfaces.
- `invariants` describe properties that must remain true after compliant edits.
- `anchor_ids` enumerate anchors that belong to the module's semantic surface.

## Open issues

- Effects, resource constraints, and error contracts are not yet formalized.
- Sidecar-vs-inline contract storage is only fixed for the MVP.
