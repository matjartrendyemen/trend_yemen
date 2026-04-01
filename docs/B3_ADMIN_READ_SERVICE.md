# B3 — Admin Read Service

## Role
Read-only layer converting sheet rows into AdminProductRecord

## Flow
SheetsStore → AdminReadService → SmartEncoding → AdminProductRecord

## Guarantees
- No writes
- No pipeline modification

## Output
list[AdminProductRecord]
