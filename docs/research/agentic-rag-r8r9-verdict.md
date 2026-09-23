# Independent Agentic RAG R8/R9 Verdict

2026-09-23. **Quality gate: fail.** The saved run completed mechanically, but missed 3/5 substantive gold changes and reported two false functional transfers. Exact citations do not establish correct interpretation.

Scope: offline review of `output/research/r-97d443d7509247acb24903657d85ad42/{result,packet,state}.json`, six `turn-*/manifest.json` files, saved originals, and `docs/research/function-gold-set.md` G01-G15. No API calls, credentials, production execution, or tests; this verdict is the only file written.

## Evidence and Scoring Rules

- `R8:pN` abbreviates `d-a91fb0f5e81ea323a7ff1f3a6205eb2631a487d9e7122f136f70577d0c410e98:pN`; `R9:pN` abbreviates `d-043853e555b8eb90b294186ee0dba33d89997827185c6be67db6fdaf3dc2a8ef:pN`. These are fragment local IDs, not pages.
- Both saved DOCX SHA-256 hashes match the packet and gold. Independent XML extraction matches all 491 R8 and 490 R9 packet paragraphs; all 97 gold quote lines occur verbatim in the packet. Final findings agree between result and state.
- Credit requires an explicit finding matching action, object, owner and material conditions; sharing a quote or topic earns no additional gold match. `split` in finding-5 counts as a substantive change for G09, with detail limits below.
- The saved task explicitly permits omitting preserved functions. Silence is therefore neither a false change nor an explicit preservation match. The 15 selected cases are not an exhaustive document inventory.

## All 15 Gold Cases

| Gold | Expected; R8 -> R9 local evidence | Saved result and independent judgment |
|---|---|---|
| G01 | Preserved plan development; p68 -> p67 | Omitted; no direct false change to the BVA-level function. Finding-7 concerns a different owner/stage and is separately false. |
| G02 | Preserved planned audits; p69 -> p68 | Omitted; no false change; approved-plan condition remains. |
| G03 | Preserved corrective-action monitoring; p79 -> p78 | Omitted; no false change; BVA monitors plans prepared by audited-object managers. |
| G04 | Preserved external-auditor coordination; p86-p90 -> p85-p89 | Omitted; no false change; all four continuations remain, including participation rather than ownership of the competition. |
| G05 | Preserved BVA/SVK interaction; p91-p93 -> p90-p92 | Omitted; no false change. Finding-8 concerns director-level G11, not this BVA duty or the Chief Auditor's preliminary assessment. |
| G06 | Reworded DNM information request; p174 -> p188; owners p171 -> p185 | Missed. Same director, information purpose and completeness/timeliness control; removed pronouns do not change responsibility. |
| G07 | Preserved DKKM methodology; p191 -> p200; owners p185 -> p196 | Omitted; no false change. 5.5.6 -> 5.5.4 is renumbering; the director remains the owner. |
| G08 | Changed owners of plan proposals; p152 -> p164; owners p150 -> p159 | Missed. Finding-8 quotes R9:p164 but does not match R8:p152 or assess this operation; finding-5's audit-leadership change does not cover it. |
| G09 | Changed audit leadership/areas; p150,p153-p158 -> p159,p161-p172 | Detected by finding-5: new named owners and explicit IT/operational areas. Partial detail coverage: no reconciliation of old continuations with new 5.3.4. |
| G10 | Changed corrective-action oversight; p164 -> p178; owners p150 -> p159 | Missed: changed owners plus ensuring/improving monitoring. Monitoring itself already exists at R8:p426 / R9:p425 (9.58). |
| G11 | Changed SVK-results/risk-coverage assignment; p171,p175-p177 -> p159,p164-p166 | Detected by finding-8. Both subclauses and the changed named assignment are supported; exclusive transfer or cessation of DNM work is not established. |
| G12 | Changed Chief Auditor interaction/informing; p14 -> p14 | Missed. Added plan-progress subject and minimum annual frequency in 1.5; quarterly/year-end reporting remains at p136 -> p145. Finding-6 does not detect this change. |
| G13 | Reworded SVK outcome evaluation; p49 -> p48, context p44 -> p43 | Missed. Removal of the implementation parenthesis changes wording only; neither owner nor action changes. |
| G14 | Preserved plan preparation organization/submission; p129,p131 -> p138,p140 | Omitted; no direct false change. Finding-7 expressly retains submission, but falsely claims a different formation/consolidation transfer. |
| G15 | Preserved DNM consultation; p171,p178 -> p185,p189 | Omitted; no false change. 5.4.5 -> 5.4.4 is renumbering; finding-9 is an unresolved BVA-level risk, not this function changing. |

**Scores:** substantive-change recall **2/5 = 40%** (G09/G11); rewording detection **0/2 = 0%**; combined change/rewording detection **2/7 = 28.6%**. Explicit valid gold correspondences **2/15 = 13.3%**, a coverage measure, not overall accuracy. All eight preserved controls have **0/8 direct false-change allegations** and **0/8 explicit preservation matches**. The two false transfers below are outside those exact gold units; broad planning-topic overlap must not be counted twice against G01/G14. G09 earns detection credit, not a claim that every subfunction was mapped.

## All Nine Findings

| Finding | Quotes | Independent semantic verdict and decisive evidence |
|---|---:|---|
| finding-1 | 5 | `created` unsupported. R8:p104-p106 versus R9:p103-p107 proves DITAAD was **added to the structural list**. No creation act or organizational continuity proof; its own limitation acknowledges this. |
| finding-2 | 5 | Same overclaim for DOA: R9:p105 is new to the list; R8:p104-p106 supports `added_to_list`, not actual creation. |
| finding-3 | 7 | `removed_from_list` supported for the old direction-director title: R8:p107-p110 versus R9:p108-p112. The explanation overstates replacement of an entire level: DNM/DKKM directors were already listed at R8:p109-p110. No abolition/personnel succession follows. |
| finding-4 | 5 | Addition of DITAAD/DOA directors to the direct-report list is supported (R8:p107-p110; R9:p108-p112); `created` is not. Use `added_to_list`; this is related to, not independent proof of, findings 1-2. |
| finding-5 | 6 | Supported as changed textual assignment and explicit audit-area split, G09 (R8:p150,p153; R9:p159,p161-p163). Does not prove one historical person became several; omitted R9:p167-p172 preserves counterparts of old detailed tasks, though old "criteria" wording is absent. |
| finding-6 | 4 | **False transfer.** R8:p136 / R9:p145 both assign report presentation to the Chief Auditor. Preparation already belongs to the DKKM director at R8:p185,p190, corresponding to R9:p196,p199. Removed frequency wording in the preparation clause is a separate textual change, not evidence of transfer. |
| finding-7 | 3 | **False change/transfer.** Old DKKM 5.5.11 (R8:p185,p196) already contains the same consolidation/formation/submission duty as new 5.5.7 (R9:p196,p203). Chief Auditor 8.2 also remains at R8:p286 / R9:p285; 5.1.1 remains at p131 / p140. |
| finding-8 | 8 | Supported changed explicit assignment, G11: R8:p171,p175-p177 -> R9:p159,p164-p166. The limitation appropriately avoids exclusive transfer; the shared G08 sentence is not evidence that G08 was evaluated. |
| finding-9 | 10 | Retain only as `insufficient_data`, not a confirmed independence conflict or new change. R8:p77 / R9:p76 expressly condition consultation on resources and independence; the submitted quote stops before these safeguards. No same-operation/object/stage conflict is established. |

For the **eight affirmative principal claims**, **3/8 = 37.5%** have a supported category and core conclusion within the textual scope (3,5,8); **3/8** overclaim `created` (1,2,4), and **2/8** assert false transfers (6,7). This is not whole-document precision or blanket approval of every explanation, especially finding-3. Finding-9 is a separate appropriate abstention, not a positive discovery. No confirmed loss, duplication or independence conflict is established by these findings.

The decisive verbs must remain distinct: R8:p190 already says "готовит отчеты", whereas R8:p136 and R9:p145 say "представляет отчеты". R8:p196 and R9:p203 both say "консолидирует полученные предложения по плану, формирует план работ БВА и представляет на рассмотрение Главному аудитору;". Existing preparation and presentation stages cannot establish a new owner transfer.

## Quotes and Owners

**Literal quote score: 53/53 = 100%** case-sensitive substrings, across **42 distinct fragments**; all IDs exist, match the claimed before/after role and occur in saved `read_ids`. **48/53** are entire paragraph texts; five are excerpts: finding-7 R8:p286 and finding-9 R8:p59,p77 / R9:p58,p76. Repeated citations count as occurrences, not independent corroboration. Exact excerpting can omit decisive conditions, as finding-9 demonstrates.

**Owner literal score: 18/18 = 100%** occur in their side's cited quotes. **Entity/role-valued fields: 14/18 = 77.8%**; four fields (both sides of findings 3-4) contain the entire subordination sentence instead of an entity. Even valid entity labels in findings 6-7 do not prove the asserted transfer. BVA is a functional block, a director is a position, and the new 5.3 heading names a group of positions; they are not interchangeable. Actual people, legal creation, succession and exclusive real-world authority remain unverified, so no real-entity correctness percentage is justified.

## Actual Saved Usage and Time

Provider-reported usage from every saved chat manifest, independently summed and equal to result/state usage; returned model `gpt-5.4-2026-03-05`, reasoning effort `none`, reported reasoning tokens 0. These are historical records, not new calls or estimates.

| Turn | Prompt | Cached prompt (subset) | Completion | Total | Manifest duration, s |
|---|---:|---:|---:|---:|---:|
| 001 | 1,516 | 0 | 13 | 1,529 | 1.167 |
| 002 | 2,032 | 0 | 60 | 2,092 | 1.363 |
| 003 | 210,702 | 0 | 64 | 210,766 | 3.627 |
| 004 | 433,519 | 209,536 | 5,860 | 439,379 | 46.448 |
| 005 | 439,552 | 432,768 | 5,491 | 445,043 | 35.748 |
| 006 | 445,110 | 438,912 | 5,494 | 450,604 | 34.971 |
| Total | **1,532,431** | **1,081,216** | **16,982** | **1,549,413** | **123.324** |

Uncached chat prompt: **451,215**; cached tokens must not be added again. Saved `index.usage.build` records **86,879 embedding tokens**, **31 successful provider requests**, **983 embedded texts**, `text-embedding-3-small`, no cache hit and complete token reporting; query usage is zero. Combined recorded provider usage: **1,636,292 tokens and 37 requests** (6 chat + 31 embedding). This is token accounting, not a monetary bill; no price assumption is made.

Chat-manifest span: **124.117 s** (15:02:50.931738 to 15:04:55.048921, +05:00). State research budget elapsed: **124.312 s**; index-build journal: **18.906 s**; state creation-to-update wall time: **143.266 s** (15:02:31.914262 to 15:04:55.180240, +05:00). These intervals have different boundaries and overlap; do not sum all of them. The 300 s budget is a limit, not elapsed time.

The trace contains one `list_documents`, two whole-document `read_context` calls and three `submit_findings` attempts; two submissions were rejected before final acceptance. There are no searches, query embeddings, hypothesis updates or recorded hypotheses. All 981 fragments were returned, but this proves delivery only. `completed`, empty final validation errors/gaps and 100% recorded reading do not repair missed correspondences, omitted counterevidence or unsupported interpretations. This single run does not evaluate retrieval ranking or establish production reliability.

## Final Follow-up: r-5a6c95ba93324ab88cdfa7729c2112c5

Offline comparison of this run's result/packet/state, eight manifests and saved sources; finding IDs below belong to the **new run**. Packet bytes are identical to the first run; saved original hashes match, and final findings agree between result/state. **Quality gate still fails: substantive gold recall falls from 2/5 (40%) to 0/5.**
The saved system prompt adds retained-assignment checks, distinct preparation/presentation stages, list-only classifications and entity-valued owners; task/model parameters are unchanged. This is **not an isolated prompt-only experiment**: manifest code hashes also differ for `server.py`, `research_state.py` and `research_agent.py`. One run per condition cannot establish causation.

| Gold coverage (all 15; same local IDs as above) | New result |
|---|---|
| G01, G02, G03, G04, G05, G07, G14, G15: preserved | All omitted; 0/8 direct false changes and 0/8 explicit preservation matches. Omission remains allowed. |
| G06, G13: reworded | Both missed, 0/2; no corresponding finding. |
| G08: plan proposals, R8:p152 -> R9:p164 | Missed again; structural-list findings do not match this action/owner change. |
| G09: audit leadership, R8:p150,p153-p158 -> R9:p159,p161-p172 | Regression: old finding-5 detected it; no new finding does. Textual responsibility changes need no proof of legal succession. |
| G10: corrective-action oversight, R8:p164 -> R9:p178 | Missed again, including changed owners and monitoring-system responsibilities. |
| G11: SVK results/coverage, R8:p171,p175-p177 -> R9:p159,p164-p166 | Regression: old finding-8 detected it; absent now. |
| G12: Chief Auditor informing, R8:p14 -> R9:p14 | Missed again; new findings 6-7 concern subsidiary conflict disclosures, a different function. |

| New finding | Quotes | Independent source verdict |
|---|---:|---|
| finding-1 | 7 | Supported `added_to_list`, DITAAD: R8:p104-p106 -> R9:p103-p104. Corrects old `created` overclaim. |
| finding-2 | 7 | Supported `added_to_list`, DOA: R8:p104-p106 -> R9:p103,p105. Corrects old `created` overclaim. |
| finding-3 | 9 | Supported removal of the old title from direct reports: R8:p107-p110 -> R9:p108-p112. DNM/DKKM directors already existed; no abolition or wholesale replacement follows. |
| finding-4 | 8 | Structural-list change is true (R8:p104-p106 -> R9:p103-p107), but duplicates findings 1-2 and is wrongly grouped `function/changed`; no action/object change is identified. Saved retries show relabeling after category/group rejection. |
| finding-5 | 3 | **Confirmed false positive:** allegedly added 4.1 at R9:p131 is verbatim R8:p124, with identical owner context R8:p123 / R9:p130. The cited old heading omits its immediately following retained assignment. |
| finding-6 | 5 | Supported addition outside gold: BVA disclosure in reports/plan under the subsidiary dual-role conditions, R8:p127 -> R9:p134-p135. A disclosure obligation is not evidence of an actual conflict. |
| finding-7 | 5 | Supported addition outside gold: dual-role information in declarations/statements, R8:p127 -> R9:p134,p136; same conditional scope. Actual dual appointments remain unproved. |

Gold change/rewording coverage is **0/7**, explicit correspondences **0/15**. Of seven affirmative findings, **5/7 (71.4%)** have supported classification/core conclusions (1,2,3,6,7), one is true but duplicated/misgrouped (4), and **1/7 (14.3%)** is a false change (5). Old false transfers (old 6-7) disappear, but retained-assignment checking still fails at new 5. Zero `created` claims is an improvement; losing both true gold detections is a regression. These distinct output sets do not establish general precision improvement.
Quotes: **44/44 exact full paragraphs**, **26 unique fragments**, correct sides and saved reading for all; per-finding counts are above (previously 53/53 exact, 48 full, 42 unique). Owners: **14/14 literal and entity/role-valued**, improved from 18/18 literal but 14/18 entity-valued; generic R8 BVA context in findings 6-7 does not establish that the new duties already existed. Real-world identity/succession remains unverified.
Eight manifests, matching result/state usage: actual model **`gpt-5.4-2026-03-05`**, effort `none`, reasoning tokens 0; **2,799,679 prompt + 21,600 completion = 2,821,279 chat tokens**, versus 1,549,413 previously. Cached prompt **2,215,680** is a subset; uncached prompt **583,999**. Embedding build again used **86,879 tokens / 31 requests**, `text-embedding-3-small`, no cache hit, no query embeddings: combined **2,908,158 tokens / 39 provider requests**, versus 1,636,292 / 37. These are saved actual usage records, not estimates or a monetary bill.
Time: manifest-duration sum **152.840 s**, manifest span **154.243 s**, state agent elapsed **154.532 s**, index build **20.500 s**, creation-to-update wall **175.069 s** (15:07:34.894879 to 15:10:29.963390, +05:00), versus 143.266 s wall previously. Overlapping intervals must not be added.
Actual trace: **8 model / 8 tool calls**: one list, two full-document reads, one coverage call, four submissions (three rejected); **zero searches/hypothesis updates**, empty hypotheses, 981/981 fragments returned. Final status is `insufficient_data`, with three gaps and no final validation errors; the attempted conflict finding was dropped during retries. That cautious status does not repair false change 5 or gold omissions. No API calls, tests or production changes were made for this comparison; only this appendix was written.
