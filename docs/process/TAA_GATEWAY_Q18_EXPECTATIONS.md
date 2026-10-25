# [Descriptive] Q18 rule-derived expected outcomes

[Descriptive] Authored before policy edits or pre-change tests. These are normative expectations from the owner ruling and existing Q13/Q17.1/Q1, not implementation observations. Each row applies independently to reference, core, MCP and conventional; exact live states remain immutable archived inputs.

| Case | Call | Expected disposition | Rule |
|---|---|---|---|
| Q18-LD03131469-OR01 | report {"amount": 120, "asserts": ["return_item_received"], "basis": "return", "case": "CL1", "cites": "CL1,ORD1,PAY1,RET1", "claim": "CL1", "customer": "K1", "prose": "Please review the $120 return-refund claim for K1.", "record": "CL1", "to": "F"} | HOLD | unknown assertions |
| Q18-LD03131469-OR02 | read_record {"record": "ORDR1"} | HOLD | Q18 primary unknown |
| Q18-LD03131469-OR03 | deny_refund {"amount": 250, "basis": "Carrier record confirms delivery and zero failed value; nondelivery is not substantiated.", "cites": "DEL2 v2; ORD2 v1", "claim": "CL2", "customer": "K2"} | REFUSE | Q13 denial basis |
| Q18-LD03131469-OR04 | report {"basis": "Review whether to uphold denial of nondelivery refund.", "claim": "CL2", "record": "DEL2 v2; ORD2 v1", "to": "F"} | PERMIT | Q18 unresolved optional reference |
| Q18-LD03131469-OR05 | report {"basis": "Release authorization received for the $250 nondelivery refund; please resolve.", "claim": "CL2", "record": "DEL2 v2", "to": "F"} | PERMIT | Q18 unresolved optional reference |
| Q18-LD03131469-OR06 | deny_refund {"amount": 120, "basis": "Return eligibility not established: return receipt RET1 records received=false.", "claim": "CL1", "customer": "K1", "record": "RET1", "template": "refund_denied"} | REFUSE | Q13 denial basis |
| Q18-assert-report-true | report {"asserts": ["return received"], "claim": "CL1", "to": "F"} | PERMIT | PR1 and Q1; unknown is not satisfied |
| Q18-assert-report-false | report {"asserts": ["return received"], "claim": "CL1", "to": "F"} | PROHIBIT | PR1 and Q1; unknown is not satisfied |
| Q18-assert-report-unknown | report {"asserts": ["return_item_received"], "claim": "CL1", "to": "F"} | HOLD | PR1 and Q1; unknown is not satisfied |
| Q18-assert-message_party-true | message_party {"asserts": ["return received"], "claim": "CL1", "template": "claim_referred", "to": "K1"} | PERMIT | PR1 and Q1; unknown is not satisfied |
| Q18-assert-message_party-false | message_party {"asserts": ["return received"], "claim": "CL1", "template": "claim_referred", "to": "K1"} | PROHIBIT | PR1 and Q1; unknown is not satisfied |
| Q18-assert-message_party-unknown | message_party {"asserts": ["return_item_received"], "claim": "CL1", "template": "claim_referred", "to": "K1"} | HOLD | PR1 and Q1; unknown is not satisfied |
| Q18-assert-issue_refund-true | issue_refund {"amount": 120, "asserts": ["return received"], "basis": "return", "claim": "CL1", "to": "K1_card"} | PERMIT | PR1 and Q1; unknown is not satisfied |
| Q18-assert-issue_refund-false | issue_refund {"amount": 120, "asserts": ["return received"], "basis": "return", "claim": "CL1", "to": "K1_card"} | PROHIBIT | PR1 and Q1; unknown is not satisfied |
| Q18-assert-issue_refund-unknown | issue_refund {"amount": 120, "asserts": ["return_item_received"], "basis": "return", "claim": "CL1", "to": "K1_card"} | HOLD | PR1 and Q1; unknown is not satisfied |
| Q18-assert-missing-evidence | report {"asserts": ["return received"], "claim": "CL1", "to": "F"} | HOLD | PR1 missing evidential fact |
| Q18-read-owned | read_record {"record": "ORD1"} | PERMIT | Q18 primary record; Q17.1 customer scope |
| Q18-read-foreign | read_record {"record": "ORD2"} | REFUSE | Q18 primary record; Q17.1 customer scope |
| Q18-read-missing | read_record {"record": "NONE"} | HOLD | Q18 primary record; Q17.1 customer scope |
| Q18-read-missing-with-forged-customer | read_record {"claim": "CL1", "customer": "K1", "record": "NONE"} | HOLD | Q18 primary record; Q17.1 customer scope |
| Q18-read-foreign-with-in-scope-claim | read_record {"claim": "CL1", "record": "ORD2"} | REFUSE | Q18 primary record; Q17.1 customer scope |
| Q18-primary-unknown-report | report {"claim": "NONE", "customer": "K1", "record": "ORD1", "to": "F"} | HOLD | Q18 unresolved primary cannot be repaired by an optional reference or asserted customer |
| Q18-primary-unknown-message_party | message_party {"claim": "NONE", "record": "ORD1", "template": "claim_referred", "to": "K1"} | HOLD | Q18 unresolved primary cannot be repaired by an optional reference or asserted customer |
| Q18-optional-report-absent | report {"claim": "CL1", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-report-unresolved | report {"claim": "CL1", "record": "NONE", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-report-prose | report {"claim": "CL1", "record": "RET1 v1; ORD1 v1", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-report-owned | report {"claim": "CL1", "record": "RET1", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-report-foreign | report {"claim": "CL1", "record": "ORD2", "to": "F"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-optional-issue_refund-absent | issue_refund {"amount": 120, "basis": "return", "claim": "CL1", "to": "K1_card"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-issue_refund-unresolved | issue_refund {"amount": 120, "basis": "return", "claim": "CL1", "record": "NONE", "to": "K1_card"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-issue_refund-prose | issue_refund {"amount": 120, "basis": "return", "claim": "CL1", "record": "RET1 v1; ORD1 v1", "to": "K1_card"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-issue_refund-owned | issue_refund {"amount": 120, "basis": "return", "claim": "CL1", "record": "RET1", "to": "K1_card"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-issue_refund-foreign | issue_refund {"amount": 120, "basis": "return", "claim": "CL1", "record": "ORD2", "to": "K1_card"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-optional-message_party-absent | message_party {"claim": "CL1", "template": "claim_referred", "to": "K1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-message_party-unresolved | message_party {"claim": "CL1", "record": "NONE", "template": "claim_referred", "to": "K1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-message_party-prose | message_party {"claim": "CL1", "record": "RET1 v1; ORD1 v1", "template": "claim_referred", "to": "K1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-message_party-owned | message_party {"claim": "CL1", "record": "RET1", "template": "claim_referred", "to": "K1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-message_party-foreign | message_party {"claim": "CL1", "record": "ORD2", "template": "claim_referred", "to": "K1"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-optional-hold_refund-absent | hold_refund {"claim": "CL1", "missing": "pending review"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-hold_refund-unresolved | hold_refund {"claim": "CL1", "missing": "pending review", "record": "NONE"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-hold_refund-prose | hold_refund {"claim": "CL1", "missing": "pending review", "record": "RET1 v1; ORD1 v1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-hold_refund-owned | hold_refund {"claim": "CL1", "missing": "pending review", "record": "RET1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-hold_refund-foreign | hold_refund {"claim": "CL1", "missing": "pending review", "record": "ORD2"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-optional-deny_refund-absent | deny_refund {"amount": 120, "basis": "RET1", "claim": "CL1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-deny_refund-unresolved | deny_refund {"amount": 120, "basis": "RET1", "claim": "CL1", "record": "NONE"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-deny_refund-prose | deny_refund {"amount": 120, "basis": "RET1", "claim": "CL1", "record": "RET1 v1; ORD1 v1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-deny_refund-owned | deny_refund {"amount": 120, "basis": "RET1", "claim": "CL1", "record": "RET1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-deny_refund-foreign | deny_refund {"amount": 120, "basis": "RET1", "claim": "CL1", "record": "ORD2"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-optional-close_case-absent | close_case {"case": "CL1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-close_case-unresolved | close_case {"case": "CL1", "record": "NONE"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-close_case-prose | close_case {"case": "CL1", "record": "RET1 v1; ORD1 v1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-close_case-owned | close_case {"case": "CL1", "record": "RET1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-close_case-foreign | close_case {"case": "CL1", "record": "ORD2"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-optional-offer_duty-absent | offer_duty {"duty": "D_resolve(CL1)", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-offer_duty-unresolved | offer_duty {"duty": "D_resolve(CL1)", "record": "NONE", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-offer_duty-prose | offer_duty {"duty": "D_resolve(CL1)", "record": "RET1 v1; ORD1 v1", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-offer_duty-owned | offer_duty {"duty": "D_resolve(CL1)", "record": "RET1", "to": "F"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-offer_duty-foreign | offer_duty {"duty": "D_resolve(CL1)", "record": "ORD2", "to": "F"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-optional-accept_duty-absent | accept_duty {"duty": "D_resolve(CL1)"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-accept_duty-unresolved | accept_duty {"duty": "D_resolve(CL1)", "record": "NONE"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-accept_duty-prose | accept_duty {"duty": "D_resolve(CL1)", "record": "RET1 v1; ORD1 v1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-accept_duty-owned | accept_duty {"duty": "D_resolve(CL1)", "record": "RET1"} | PERMIT | Q18 optional reference and complete-path customer scope |
| Q18-optional-accept_duty-foreign | accept_duty {"duty": "D_resolve(CL1)", "record": "ORD2"} | REFUSE | Q18 optional reference and complete-path customer scope |
| Q18-unruled-export-unresolved | export_records {"record": "NONE"} | REFER | Existing no-authorization-rule referral retained |
| Q18-unruled-export-foreign | export_records {"record": "ORD2"} | REFER | Existing no-authorization-rule referral retained |
| Q18-denial-deny_refund-empty | deny_refund {"amount": 120, "basis": "", "claim": "CL1"} | REFUSE | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-deny_refund-missing-record | deny_refund {"amount": 120, "basis": "NONE", "claim": "CL1"} | REFUSE | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-deny_refund-prose | deny_refund {"amount": 120, "basis": "Return eligibility is not established", "claim": "CL1"} | REFUSE | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-deny_refund-valid | deny_refund {"amount": 120, "basis": "RET1", "claim": "CL1"} | PERMIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-deny_refund-versioned | deny_refund {"amount": 120, "basis": "RET1@v1", "claim": "CL1"} | PERMIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-deny_refund-contradicting | deny_refund {"amount": 120, "basis": "RET1", "claim": "CL1"} | PROHIBIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-deny_refund-unrelated | deny_refund {"amount": 120, "basis": "DEL2", "claim": "CL1"} | PROHIBIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-message_party-empty | message_party {"amount": 120, "basis": "", "claim": "CL1", "template": "refund_denied", "to": "K1"} | REFUSE | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-message_party-missing-record | message_party {"amount": 120, "basis": "NONE", "claim": "CL1", "template": "refund_denied", "to": "K1"} | REFUSE | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-message_party-prose | message_party {"amount": 120, "basis": "Return eligibility is not established", "claim": "CL1", "template": "refund_denied", "to": "K1"} | REFUSE | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-message_party-valid | message_party {"amount": 120, "basis": "RET1", "claim": "CL1", "template": "refund_denied", "to": "K1"} | PERMIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-message_party-versioned | message_party {"amount": 120, "basis": "RET1@v1", "claim": "CL1", "template": "refund_denied", "to": "K1"} | PERMIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-message_party-contradicting | message_party {"amount": 120, "basis": "RET1", "claim": "CL1", "template": "refund_denied", "to": "K1"} | PROHIBIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-denial-message_party-unrelated | message_party {"amount": 120, "basis": "DEL2", "claim": "CL1", "template": "refund_denied", "to": "K1"} | PROHIBIT | Q13 missing evidence versus contradiction; implicit/explicit template parity; Q1 precedence |
| Q18-report-cites-unresolved | report {"cites": "NONE", "claim": "CL1", "to": "F"} | PERMIT | Q18 applies to resolved citations as well as record |
| Q18-report-cites-foreign | report {"cites": "ORD2", "claim": "CL1", "to": "F"} | REFUSE | Q18 applies to resolved citations as well as record |
| Q18-path-all-allowed | report {"claim": "CL1", "record": "ORD2", "to": "F"} | PERMIT | Q17.1 complete-path existential choice and Q18 all resolved references |
| Q18-path-parent-restricted | report {"claim": "CL1", "record": "ORD2", "to": "F"} | REFUSE | Q17.1 complete-path existential choice and Q18 all resolved references |
| Q18-path-split-paths | report {"claim": "CL1", "record": "ORD2", "to": "F"} | REFUSE | Q17.1 complete-path existential choice and Q18 all resolved references |
| Q18-path-independent-complete-path | report {"claim": "CL1", "record": "ORD2", "to": "F"} | PERMIT | Q17.1 complete-path existential choice and Q18 all resolved references |
| Q18-category-not-reference | issue_refund {"amount": 120, "basis": "return", "claim": "CL1", "to": "K1_card"} | PERMIT | Q18 registered reference semantics, not string coincidence |
| Q18-primary-unrestricted-report | report {"claim": "NONE", "to": "F"} | HOLD | Q18 primary object must resolve, including under an unrestricted path |
| Q18-primary-unrestricted-read | read_record {"record": "NONE"} | HOLD | Q18 unknown primary is unknown, never unbounded permission |
| Q18-unrestricted-resolved-reference | report {"claim": "CL1", "record": "ORD2", "to": "F"} | PERMIT | Q18 both resources satisfy an unrestricted path |
| Q18-reference-claim-dimension-same | message_party {"claim": "CL1", "record": "CL1", "template": "claim_referred", "to": "K1"} | PERMIT | Q18 and Q17.1 every applicable dimension; same customer does not erase claim scope |
| Q18-reference-claim-dimension-other | message_party {"claim": "CL1", "record": "CL2", "template": "claim_referred", "to": "K1"} | REFUSE | Q18 and Q17.1 every applicable dimension; same customer does not erase claim scope |

[Descriptive] Additional engineering controls, authored before their execution:

| Control | Rule-derived expectation | Pre-change target |
|---|---|---|
| Optional reference becomes resolved after proposal | PERMIT while absent; insertion invalidates the old token; no old-token commit; fresh proposal REFUSE when the new reference is out of scope | All four paths; old core/MCP incorrectly HOLD before insertion, old reference/conventional incorrectly PERMIT after insertion |
| Agent-supplied internal resource-context field | Never adopted as trusted reference or primary-unknown context | Generic trust boundary; new registry contract control |
| Malformed trusted reference callback | Fail closed on non-list, non-object or unregistered dimensions | New callback contract control |
