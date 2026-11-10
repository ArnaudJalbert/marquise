# Privacy operations

Owner: Arnaud Jalbert. Public contact: `me@arnaudjalbert.com`.

This is the operating procedure for the policy work in [#415](https://github.com/ArnaudJalbert/marquise/issues/415). It implements proportionate safeguards for a personal hobby. It does not assert that Marquise is an enterprise or certify compliance with any law. The [research record](research/2026-11-01-policy-and-source-review.md) contains the legal/source evidence and accepted risks.

## Configuration and processing inventory

| Processing | Control or known fact | Verification still needed |
|---|---|---|
| Routine web access logs | Nginx `access_log off` in the proposed configuration | Verify after deployment; not changed on live machines by this PR |
| Routine API access logs | Production Uvicorn command uses `--no-access-log` | Verify after deployment; the structured application logger and error diagnostics remain |
| Application/error output | Fly publishes a fixed seven-day application-log retention period | Check for separately exported copies before claiming seven days covers all copies |
| External images | Web responses set `Referrer-Policy: no-referrer` | Image hosts still receive connection information, including IP addresses |
| Contact email | Arnaud confirms the alias forwards to his personal Gmail; the domain is managed through Squarespace | Identify the actual forwarding service; a domain registrar is not necessarily the email forwarder |
| Authentication and edit history | Login and manual editing are removed from the application; the account-linked records and the two write tables are planned for deletion in the same release, with no new archive | Confirm the live deletion completes; provider backups may retain copies until their own expiry |
| Catalog database | A Fly database is prepared; repository documentation does not establish API cutover | Confirm the live connection destination without recording credentials |

Fly states that its own proxy log store does not retain inbound client IPs. This does not mean application/error output cannot contain an address. Its platform processing also extends beyond the selected Machine region. Keep those distinctions in disclosures. [Fly security questionnaire, COMPLIANCE-12 and COMPLIANCE-23](https://fly.io/legal/security-questionnaire/).

Read-only Fly machine inspection on 2026-11-01 found the API and interface Machines in `yyz`, with no explicit command override. The API Machines were stopped; one interface Machine was started. No visitor logs or secret values were retrieved. These observations do not verify container-level logging or all processors, and stopped Machines must not be started just to collect evidence without a reason.

## Retention and access

- Support email: Arnaud adopted deletion when no longer needed, without a fixed period. When closing a support request, review the message and attachments for any remaining request, dispute, or legal purpose. Delete them from the Gmail mailbox when none remains. If preservation is necessary, record the reason and review it when that purpose ends. Do not promise a 90-day timer, immediate erasure of provider backups, or deletion of unrelated personal email. This PR does not access or clean the mailbox.
- Application output on Fly: rely on its published platform expiry, with no additional log export configured by this work. If an export is added, record its purpose, destination, access, and expiry before using it. Do not claim an export does not exist merely because this PR does not add one.
- Account, edit-history, and replay data: login and manual editing are removed from the application. The account-linked records and the two write tables are planned for deletion in the same release, with no new archive. Do not promise immediate erasure from provider backups or claim the live deletion is already complete before it is verified.
- Case records: keep only what is necessary for a request, complaint, or incident. Store real records in an access-controlled location outside Git, research notes, issue comments, and chat. Never put a requester's documents, message contents, IPs, or account tokens in a public or broadly shared tracker.

The preceding inventory is intentionally explicit about unimplemented purge rules. Documentation is not evidence of a completed mailbox cleanup, an enabled timer, or a provider agreement.

## Privacy requests and complaints

1. Arnaud reviews requests arriving at the approved alias. Record receipt date, request category, due date, responsible person, and status in a private case record. Acknowledge receipt and ask only for information needed to locate the records and verify the requester proportionately.
2. Classify the request as access, correction, deletion, withdrawal of consent, or complaint. Search the relevant email, account, audit, log, and provider records. Do not require government identification by default or collect unrelated sensitive information.
3. Assess applicable rights, retention duties, other people's information, and technical constraints. A deletion request does not automatically authorize destroying every linked audit/replay record. Escalate uncertainty rather than promising an unconditional outcome.
4. Target a substantive response within 30 days. If a different legal deadline or exception applies, record the reason. Explain the result and any permitted refusal or review route in plain language. The 30-day statutory rule is conditional on legal coverage. [CAI access and scope guidance](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/champ-application-loi_entreprises).
5. Record actions and completion date without duplicating the underlying personal information. Correct relevant records and notify processors when necessary. Apply the adopted case-retention rule when the purpose ends; preserve only documented dispute/legal exceptions.

No messages are sent by this implementation. Actual correspondence requires a real request and the owner's authority.

## Confidentiality incidents

1. Contain suspected exposure, preserve only necessary evidence, and involve affected providers. Rotate or revoke credentials when justified, without deleting evidence or shutting down unrelated services reflexively.
2. Open a private register entry even if the incident is ultimately assessed as low risk. Record awareness date, incident dates, information categories, affected systems, approximate affected count, cause, containment, and the owner.
3. Assess sensitivity, likely consequences, and likelihood of harmful use. Document the assessment, including the basis for any conclusion that there is no serious-harm risk.
4. If the applicable law requires notification, notify CAI and affected people promptly when the serious-harm threshold is met. Record dates, recipients, contents, provider actions, and outstanding remediation. Do not invent an incident or notify anyone merely because this procedure exists.
5. If Québec's private-sector law applies, retain the register information for at least five years after awareness, with restricted access. Reassess unresolved actions and prevent recurrence. [CAI incident guidance](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/incidents-confidentialite-mesures-securite-entreprises).

Private register fields:

```text
case id | awareness date | incident dates | owner | systems
information categories | affected count | cause | containment
harm assessment and reasons | notifications and dates | remediation
closure date | applicable retention basis | review/destruction date
```

This is a schema for the private register, not a place to store incidents in Git.

## Provider and transfer review

Before adding a provider or changing processing, record the service, information categories, purpose, regions/support access, retention, deletion/export controls, relevant contract/DPA, and incident contact. Review only the necessary settings; never paste secrets or personal records into the inventory.

If Québec's private-sector law applies, complete the proportionate privacy assessment and written safeguards required for qualifying projects and processing outside Québec. Toronto is outside Québec. A public privacy statement does not replace an applicable contractual arrangement. [Private-sector law, sections 3.3, 17 and 18.3](https://www.legisquebec.gouv.qc.ca/en/document/cs/p-39.1).

## Québec applicability assessment

Known owner-supplied facts: personal hobby, no business or organization, free and non-commercial, Montréal coverage, independent public API use, and a personal contact inbox. No commercial relationship or payment handling was identified. These are operating facts, not conclusions about legal status.

**Privacy.** CAI uses the organized economic activity test in Civil Code article 1525, which can include non-commercial activity. The absence of a company or revenue therefore does not conclusively resolve coverage. Providing a maintained public service/API points toward organized service activity; the hobby purpose and lack of an identified economic activity point the other way. No official ruling was found that decides this particular fact pattern. The remaining question is whether this activity is economic and sufficiently organized within the applicable test. [CAI enterprise guidance](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/champ-application-loi_entreprises).

**French.** OQLF's guidance addresses enterprises operating in Québec. If Marquise is within that scope, service duties may extend beyond translating the policies. We have not established an applicable hobby exemption or a definite obligation for this site. Arnaud chose assessment before adding French, so this work does not introduce a language switch or assert that English-only publication is legally cleared. [OQLF language-of-service guidance](https://www.oqlf.gouv.qc.ca/francisation/entreprises/langue-de-service.html).

**Result.** Coverage remains conditional, not proven either way. The implemented safeguards stand on their own. A focused regulator or Québec counsel answer is needed if the owner requires certainty before publication. No enterprise registration, French expansion, or legal certification is implied by this PR. Reassess upon monetization, sponsorship, organizational change, new tracking, or expanded personal-data processing.

Prepared scope question for the owner to review and send if desired:

> I personally maintain a free, non-commercial Montréal showtime guide and public API as a hobby, without a business or organization. It does not sell tickets or offer visitor accounts. Hosting processes technical request information; support reaches my personal email. Manual editing and its account-linked change history are removed from the application and scheduled for deletion in the same release, with no new archive. Does this activity fall within your enterprise scope, and which facts determine that conclusion?

This inquiry has not been sent. Do not contact a regulator or lawyer on the owner's behalf without authorization.

## Deployment and publication checklist

- Verify effective access-log flags, Nginx configuration, and the no-referrer header after a separately authorized deployment. Do not print visitor log contents to prove logging behavior.
- Confirm the forwarding service, processor arrangements, and relevant account/audit retention. Apply the adopted support-email procedure manually; no mailbox timer or cleanup automation is installed by this PR.
- Arnaud approved the information-page copy on 2026-11-01 and authorized removing its draft labels and marking PR #416 ready for review. This is not merge or deployment authority, or legal clearance. Make sure public copy matches the deployed configuration and adopted practices before publication; future material wording changes require review.
- Keep the separately accepted Cineplex and Cinémathèque risks settled. An affiliation disclaimer and source credit do not create downstream content rights.
- Keep [#410](https://github.com/ArnaudJalbert/marquise/issues/410) separate. The current metadata patch contract preserves `None` values and lacks per-field provenance; expiry must not erase cinema-supplied values or pretend failed refreshes made old values fresh.
