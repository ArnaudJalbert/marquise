# Marquise policy and source review

Research date: 2026-11-01. This is a research record for [policy proposal #415](https://github.com/ArnaudJalbert/marquise/issues/415), not approved policy text or a legal determination. It combines three parallel investigations of privacy, content licensing, and website obligations.

Code reviewed during research: `origin/main` at `f80ba0edff2790546668dd65cc1ef1a6d9784e8d`. Research began in the older footer worktree at `bc5d20bd5d97325d70dda090a1654e2dca6ea709`. Findings below use the reviewed main revision. No production logs, credentials, provider accounts, or private agreements were inspected. The research phase made no website or deployment changes. A subsequent branch implements the information pages and includes this note; final copy approval is recorded in the implementation update below.

## What needs attention first

1. Verify all server logging before approving privacy claims. The custom completion log is only one channel; committed containers retain separate access-log defaults.
2. Resolve whether this personal project is an enterprise under the relevant Québec laws. Free access does not settle that question. Privacy, French-language, and registration consequences require separate applicability analysis.
3. Review cinema synopses and images separately from showtime facts. Cinémathèque's explicit restriction has now received its own risk decision, recorded below.
4. Complete TMDB attribution and the separately tracked cache work. Check every persisted TMDB-derived field, including what happens when refresh fails.
5. Establish actual retention, provider, and request-handling practices before promising them in a policy.

The evidence and qualifications for these recommendations follow. None is a finding that every listed law applies to Marquise.

## Decisions already settled

Marquise is to remain free and non-commercial. The approved public contact is `me@arnaudjalbert.com`. Arnaud approved identifying himself as responsible for protection of personal information. He accepts the unresolved Cineplex contractual/access risk, wants to retain Cineplex, and wants public copy to credit the source without describing collection methods or implying affiliation or permission. These are recorded in [proposal #415](https://github.com/ArnaudJalbert/marquise/issues/415).

Arnaud also explicitly requests public wording stating that Marquise is not officially affiliated with Cineplex, TMDB, or any other referenced cinema, ticket provider, or source website. Credits and booking links must not imply a partnership or endorsement. This supplements the required TMDB notice.

This research does not reopen that decision. A separate source's restrictions or a separate use of expressive material should not silently be treated as covered by that acceptance.

After reading the findings, Arnaud explicitly chose to keep Cinémathèque and accept its separate collection/reuse risk. This settles that source decision without claiming permission or changing the underlying terms.

Arnaud also explained that the contact alias uses a Squarespace-managed domain and forwards to his personal Gmail inbox. He adopted deletion of support messages when no longer needed, without a fixed retention period. The actual forwarding service and its processing locations remain unverified. The [operating procedure](../privacy-operations.md) specifies manual review and deletion; this work has not accessed or cleaned the mailbox.

## Implementation update

Arnaud subsequently requested implementation of the remaining measures. The policy branch now disables routine Nginx/Uvicorn access logging, sets a no-referrer policy, adds reuse/non-affiliation guidance and policy links to the API reference, and includes the [privacy operating procedure and Québec scope assessment](../privacy-operations.md). Arnaud approved the final information-page copy on 2026-11-01; its draft labels are removed and PR #416 is to be marked ready for review. These configuration changes have not been deployed. Copy approval is not merge/deployment authority or legal clearance.

Read-only Fly inspection confirmed `yyz` Machines and no custom command overrides; it did not read visitor logs or prove container-level settings. Fly's current questionnaire corrects the earlier platform-IP assumption: application output has seven-day retention, while its own proxy log store does not retain inbound client IPs. Application/error output must be considered separately. [Fly questionnaire, COMPLIANCE-12](https://fly.io/legal/security-questionnaire/).

Arnaud chose assessment before adding French. The documented assessment identifies the unresolved economic-activity test rather than declaring the hobby exempt or requiring a French interface without establishing scope. No regulator inquiry has been sent. #410 remains a separate backend task; safe expiry needs to address preservation semantics and source provenance.

Arnaud clarified in this research conversation on 2026-11-01 that Marquise is a personal hobby, with no business or organization, and that the public API is intended for independent public use. These are supplied operating facts, not a legal determination of enterprise status or a grant of third-party content rights.

## Verified code and configuration gaps

### Server logging is broader than the custom completion event

**Configuration finding; production behavior unverified.** The custom completion event records method, path, status, duration, and request ID, without explicit IP or query-string fields. The API container starts Uvicorn without disabling its separate access logger. Pinned Uvicorn 0.49.0 logs a client address and a request path that includes query strings. Changing the root logger does not itself establish that Uvicorn's access logger is disabled. [Marquise completion event](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/src/marquise_api/logging_middleware.py#L72-L128), [API startup](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/Dockerfile#L64), [Uvicorn 0.49 logging configuration](https://github.com/Kludex/uvicorn/blob/0.49.0/uvicorn/config.py), [HTTP access logging](https://github.com/Kludex/uvicorn/blob/0.49.0/uvicorn/protocols/http/h11_impl.py#L440-L448).

The frontend uses an official Nginx image and replaces its server configuration without overriding inherited access logging. Nginx's default combined format includes remote address, request, referrer, and user agent; the official image directs logs to stdout/stderr. That is additional server processing, beyond Fly's own processing. Runtime overrides could change it. [Frontend Dockerfile](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/web/apps/marquise-interface/Dockerfile), [Server configuration](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/web/apps/marquise-interface/nginx.conf), [Nginx logging defaults](https://nginx.org/en/docs/http/ngx_http_log_module.html), [Official image logging](https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-docker/).

**Action.** The proposed configuration now disables routine access logs. Verify this after deployment and finish the exception/export inventory. Keep #415's narrowly qualified completion-log statement; do not broaden it to "Marquise does not log IPs or queries."

### An API client address may identify a proxy

**Unknown deployment fact.** The limiter uses SlowAPI's `get_remote_address`, which reads `request.client.host`. Uvicorn's forwarded-header trust settings and the proxy path determine whether this is the visitor address. A public Fly deployment alone does not settle that behavior. [Marquise limiter](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/src/marquise_api/rate_limit.py#L41-L49), [SlowAPI helper](https://github.com/laurentS/slowapi/blob/master/slowapi/util.py), [Pinned Uvicorn proxy settings](https://github.com/Kludex/uvicorn/blob/0.49.0/uvicorn/config.py), [Fly request headers](https://docs.fly.io/networking/request-headers).

**Action.** Describe counters as using the client address available to the API until trusted proxy behavior is verified. Do not fix trust by indiscriminately trusting spoofable forwarded headers.

### Visitor browsing is different from authenticated administration

**Verified capability; actual usage unknown.** Main contains Supabase authentication, account-linked screening mutations, audit history, and account-scoped replay records. Its API description says successful idempotency keys do not expire. "No visitor accounts" can describe public browsing; "Marquise has no accounts or retained personal information" would overlook these capabilities. [Authentication wiring](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/packages/marquise-core/src/marquise/infrastructure/di/auth.py#L39-L76), [Verified write identities](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/src/marquise_api/auth.py#L65-L87), [Audit and replay behavior](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/src/marquise_api/app.py#L124-L154).

**Action.** Establish who has accounts. Cover authentication, change reasons, audit attribution, replay data, and retention in an appropriate administrator/editor notice. Avoid asking users to include personal information or secrets in change reasons.

### External posters still send connection information

**Verified code; browser and live headers untested.** Poster elements load supplied external URLs without an explicit referrer policy. Booking links use `noreferrer`, which does not govern image requests. The web standard's default generally sends the origin on secure cross-origin requests; `no-referrer` can suppress that field but cannot suppress the connection IP. [Poster rendering](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/web/packages/components/src/components/minimal/MinimalCatalogue.tsx#L22-L30), [Booking links](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/web/packages/components/src/components/minimal/Showtime.tsx#L3-L13), [W3C referrer-policy draft](https://w3c.github.io/webappsec-referrer-policy/).

**Action.** Retain the external-image disclosure. Consider an explicit no-referrer policy as a small privacy improvement. CSP and other header hardening are engineering decisions, not reasons to invent policy boilerplate.

## Québec privacy obligations depend on enterprise status

### Non-commercial does not automatically mean exempt

**Conditional applicability.** CAI explains enterprise status using Civil Code article 1525, which includes organized economic activity supplying services whether commercial or otherwise. Nonprofit organizations require a case-specific assessment. A maintained public service could merit that assessment, but its existence alone does not establish that Marquise qualifies. [CAI scope and enterprise guidance](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/champ-application-loi_entreprises).

**Action.** Use Arnaud's confirmed personal-hobby status in the assessment. Do not assume a business operator or launch an enterprise compliance program without establishing coverage. If relying on an exemption, seek a focused applicability answer rather than assuming either exemption or full coverage.

PIPEDA principally concerns commercial activities and has a separate exclusively personal/domestic exclusion. No commercial activity was identified in the stated situation; public availability alone does not prove PIPEDA applies. Reassess if monetization or commercial processing is introduced. [PIPEDA sections 2 and 4](https://laws-lois.justice.gc.ca/eng/acts/P-8.6/FullText.html), [OPC nonprofit guidance](https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/r_o_p/02_05_d_19/?wbdisable=true).

### If Québec's private-sector law applies, a name and email are only part of the work

The applicable notice includes purposes, collection means, access and rectification rights, withdrawal of consent, necessary recipient categories, and applicable communication outside Québec. Retention duration is also information available on request. The accountable role's title and contact information must be public. [CAI collection disclosures](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/collecte-renseignements-personnels_entreprises), [Québec private-sector law, sections 3.1 and 8](https://www.legisquebec.gouv.qc.ca/en/document/cs/p-39.1).

Governance includes retention/destruction, responsibilities, and complaints, with detailed information made public. A privacy notice is distinct from obtaining any necessary consent. The approved name should accompany an explicit role such as "Responsible for protection of personal information" and the approved alias. [CAI enterprise responsibilities](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/responsable-protection-renseignements-personnels-entreprise), [CAI privacy-policy guide](https://www.cai.gouv.qc.ca/uploads/pdfs/CAI_GU_POL_Confidentialite.pdf?v=1741120394).

Retention needs actual schedules covering email, logs, authentication, audit/replay data, and backups. Purpose completion generally requires destruction, subject to applicable retention duties and lawful anonymization. Access/rectification requests generally require response within 30 days. Avoid a universal deletion promise or limiting all rights to information voluntarily supplied. [CAI retention and destruction](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/conservation-destruction-renseignements-personnels), [CAI access and rectification guidance](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/citoyens-protection-renseignements-personnels/acces-et-protection-renseignements-personnels).

Incident handling requires mitigation and a register of confidentiality incidents, including incidents below the serious-harm threshold. Serious-harm risk triggers prompt notification to CAI and affected people. Register information is retained at least five years after awareness. [CAI incident guidance](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/incidents-confidentialite-mesures-securite-entreprises).

**Action.** If covered, use a proportionate private procedure and register, not a large compliance platform. Define how requests are verified, searched, answered, corrected, and closed; how incidents are assessed and escalated; and who can access the records. Public wording must describe practices that exist.

### Toronto is outside Québec; committed region is not proof of all data locations

The web/API configurations select `yyz`. Database documentation describes a prepared Fly catalog while API, import, and Supabase Auth retain their existing configurations. It does not prove the live database has moved, or that all processing takes place in Canada. [API Fly configuration](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/fly.toml), [Database migration scope](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/docs/fly-postgres.md#L1-L23).

If the law applies, section 17 requires an assessment and written agreement for applicable processing outside Québec, including another province. Section 18.3 sets safeguards for service-provider disclosures without consent. Qualifying information-system development or redesign also has assessment requirements. Provider privacy statements alone do not establish the necessary arrangements. [Québec private-sector law, sections 3.3, 17 and 18.3](https://www.legisquebec.gouv.qc.ca/en/document/cs/p-39.1), [CAI assessment guidance](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/responsable-protection-renseignements-personnels-entreprise).

**Action.** Map Fly, current database, Supabase Auth, email delivery/mailbox services, log exports, backups, subprocessors, and support access. Confirm locations and agreements before stating transfers or retention as facts. Do not collect credentials to do this inventory.

## French language, registration, and other website duties

### English-only service deserves a focused scope check

**Conditional applicability.** OQLF describes French service obligations for enterprises operating in Québec, including email. Charter articles 52 and 55 concern covered public documents and certain contracts. If Marquise is covered, translating only the policies may be insufficient. Its current HTML declares English. [OQLF language-of-service guidance](https://www.oqlf.gouv.qc.ca/francisation/entreprises/langue-de-service.html), [Charter of the French language](https://www.legisquebec.gouv.qc.ca/fr/document/lc/C-11), [Current HTML](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/web/apps/marquise-interface/index.html#L1-L6).

OQLF's disclosed 2022 internal website guidance discusses enterprise activity and a real Québec connection among its criteria. It supports asking the scope question; it is dated interpretive material, not a current ruling on this unpaid guide. The 25-employee francisation threshold is separate from language-of-service duties and is not a general small-project exemption. [Disclosed website guidance, pages 7-8](https://www.oqlf.gouv.qc.ca/rdiprp/demandes/AI2223_282/doc_diffusion_web.pdf), [OQLF legislative changes](https://www.oqlf.gouv.qc.ca/charte/changementslegislatifs/).

**Action.** Confirm scope with OQLF or Québec counsel if uncertain. If covered, plan French interface/service and applicable contract delivery, not merely a translated footer.

### Registration is a separate conditional question

Québec's registrar generally requires registration for a sole proprietorship operating under a name without the individual's given name and surname. This matters if Marquise is such an enterprise. It does not establish that this personal guide must register. The full legal-publicity statute could not be retrieved reliably, so no conclusion is drawn about exceptions. [Québec registration guidance](https://www.quebec.ca/entreprises-et-travailleurs-autonomes/demarrer-entreprise/immatriculer-constituer-entreprise/immatriculation-entreprise/a-propos), [Legal publicity statute](https://www.legisquebec.gouv.qc.ca/fr/document/lc/P-44.1).

**Action.** Confirm existing legal form and registration status alongside the enterprise question. Do not invent an obligation to publish Arnaud's home address.

### Keep the booking and liability text restrained

Consumer Protection Act merchant/consumer-contract and distance-contract duties do not establish a universal shop-style identity-disclosure checklist for all information sites. Free service also does not automatically resolve every contract question. Civil Code article 1474 limits liability exclusions, including bodily/moral injury and material injury from intentional or gross fault. [Consumer Protection Act, sections 2, 54.1 and 54.4](https://www.legisquebec.gouv.qc.ca/en/pdf/cs/P-40.1%20.pdf), [Civil Code article 1474](https://www.legisquebec.gouv.qc.ca/fr/version/lc/CCQ-1991?code=se%3A1474&history=20210906&langCont=en).

**Action.** Retain factual schedule warnings, external booking/payment/refund guidance, and the mandatory-rights saving clause in #415. Do not add blanket immunity or imply the policy overrides law. If Terms are intended as an adhesion contract, assess Charter article 55 as well. [Charter article 55](https://www.legisquebec.gouv.qc.ca/fr/version/lc/C-11?code=se%3A55).

## Source rights and attribution

### TMDB requires attribution and limited-duration caching

**Published licensing conditions.** The content researcher retrieved the public API terms and found section 3's longer notice: "This website uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB." The FAQ still displays a shorter notice. The longer contractual text is the better basis for #415, with an approved, unmodified logo less prominent than Marquise branding and a link to TMDB. [TMDB API terms, section 3](https://www.themoviedb.org/api-terms-of-use), [TMDB FAQ](https://developer.themoviedb.org/docs/faq), [Approved TMDB logos](https://www.themoviedb.org/about/logos-attribution).

Section 1.C imposes a six-month cache limit, and section 1.D requires purging on termination. The license is non-sublicensable. Non-commercial use is a licensing condition; future revenue, sponsorship, affiliate arrangements, or paid distribution need reassessment. These are published terms, not a ruling on enforceability or a guarantee of underlying image rights. [TMDB API terms, sections 1 and 2](https://www.themoviedb.org/api-terms-of-use).

**Retrieval limitation.** The researcher read full public HTML through an ordinary HTTP GET and reported the terms' October 20, 2023 update date. Browser search retrieval was blocked, and the parent's subsequent direct GET returned 403. The finding rests on that successful research retrieval, not an independently successful synthesis re-fetch. Recheck terms before implementation if access or applicable account terms differ.

During draft implementation, an ordinary unauthenticated GET successfully retrieved the official branding page and its approved blue short SVG. The local `tmdb-logo.svg` is an unchanged copy of that asset, displayed at 100px wide without altering its colors or aspect ratio. [Official branding page](https://www.themoviedb.org/about/logos-attribution), [Original SVG](https://www.themoviedb.org/assets/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg).

Current enrichment can skip existing metadata unless refresh is requested; failure can leave previous values intact. Persisted TMDB-derived fields include more than descriptions and posters. [Enrichment field selection and refresh behavior](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/packages/marquise-core/src/marquise/application/use_cases/enrich_movie.py#L52-L168).

**Action.** Correct #415's notice at implementation review. Expand [#410](https://github.com/ArnaudJalbert/marquise/issues/410) to account for every derived field and repeated refresh failures. A failed attempt must not reset the age of stale values. Inventory serving caches and retained copies; the terms do not explain treatment of inaccessible disaster-recovery backups, so do not invent an interpretation.

### Cinémathèque presents a separate explicit restriction

**Published restriction; applicability and enforceability unresolved.** Cinémathèque's terms expressly prohibit screen/data scraping and activities collecting, storing, or reorganizing site data. They also restrict text/image reproduction without written authorization and downloading to private use. This is materially more explicit than the Cineplex clause discussed earlier. [Cinémathèque conditions of use](https://www.cinematheque.qc.ca/fr/conditions-dutilisation-2/).

Main retrieves its cinema index and linked detail pages; the source also extracts synopsis text and poster URLs from a separate ticketing host. The website terms' application to that separate host was not established. No private permission was supplied for review. [Website retrieval](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/packages/marquise-core/src/marquise/infrastructure/sources/cinematheque/gateways/source.py#L354-L361), [Ticketing metadata](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/packages/marquise-core/src/marquise/infrastructure/sources/cinematheque/gateways/source.py#L266-L297).

**Decision.** Arnaud has now explicitly accepted this separate risk and chosen to keep the source. Do not reopen that decision without new evidence, equate attribution with permission, or classify robots.txt as a legal prohibition.

### Showtime facts are different from synopses and images

Cinema imports include description text and poster URLs, including Cinéma Cinéma and Cinéma Public. Those fields enter movie creation separately from screening times and ticket URLs. This means "we only gather showtime facts" is not a complete description of the code's inputs. [Cinéma Cinéma extraction](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/packages/marquise-core/src/marquise/infrastructure/sources/cinemacinema/gateways/source.py#L260-L275), [Cinéma Public extraction](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/packages/marquise-core/src/marquise/infrastructure/sources/cinemapublic/gateways/source.py#L514-L554), [Import mapping](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/packages/marquise-core/src/marquise/application/use_cases/import_screenings.py#L65-L108).

Copyright distinguishes facts from expression. Original synopses and photographs can receive protection. Non-commercial operation and a credit do not by themselves establish permission or an applicable fair-dealing exception. TMDB itself does not claim ownership of all API data/images. [CIPO copyright guide](https://ised-isde.canada.ca/site/canadian-intellectual-property-office/en/guide-copyright), [Copyright Act section 29](https://laws-lois.justice.gc.ca/eng/acts/C-42/section-29.html), [TMDB legal notice](https://developer.themoviedb.org/docs/faq).

**Action.** Inventory field provenance and the basis for reuse of expressive material. Distinguish direct image requests from copying stored images, without assuming either resolves every rights question. Retain a practical correction/removal contact. No verified reuse license was established for the other cinema sources; absence of a discovered prohibition is not proof of permission.

### Independent public API use is intended; downstream rights remain unresolved

Public movie endpoints expose descriptions, poster URLs, trailers, ratings, and vote counts. Open access does not itself grant downstream content rights. TMDB's non-sublicensable license creates a question to resolve before promoting bulk reuse, but is not proof that Marquise's frontend-serving API is prohibited. [Movie endpoints](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/src/marquise_api/routers/movies.py#L22-L82), [Response fields](https://github.com/ArnaudJalbert/marquise/blob/f80ba0edff2790546668dd65cc1ef1a6d9784e8d/apps/marquise-api/src/marquise_api/schemas/movie.py#L40-L54), [TMDB API license](https://www.themoviedb.org/api-terms-of-use).

Arnaud confirmed that independent public use is intended. This makes downstream reuse a present design requirement rather than a hypothetical future feature.

**Action.** Establish what independent consumers may do with each category of data before encouraging reuse. Distinguish showtime facts, cinema text/images, and TMDB-derived fields; do not put a blanket permissive content license over all API responses without a verified basis. State that API availability grants no additional third-party rights and link documentation to credits/source restrictions. Merely adding authentication would not settle content licensing. These are recommended next steps based on the source and license evidence above, not a finding that every independent API use is prohibited.

## Requirements not established for the present situation

- **A generic cookie banner.** A confidentiality policy and any necessary consent mechanism are distinct. A banner is not established merely because a policy is needed. Verify actual third-party behavior rather than promising that external image hosts never set cookies. [CAI privacy-policy guide](https://www.cai.gouv.qc.ca/uploads/pdfs/CAI_GU_POL_Confidentialite.pdf?v=1741120394).
- **GDPR solely because the website is globally reachable.** Territorial scope involves establishment, targeting, or relevant behavior monitoring. None was established here. [EDPB territorial-scope guidelines](https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_3_2018_territorial_scope_after_public_consultation_en_1.pdf).
- **Newsletter consent/unsubscribe machinery for requested support replies.** The CASL regulation excludes responses to requested inquiries or complaints from section 6. Do not turn support addresses into a mailing list. Reassess any future newsletter by content and commercial purpose. [Regulation section 3(b)](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2013-221/FullText.html), [CRTC CASL FAQ](https://crtc.gc.ca/eng/com500/faq500.htm).
- **Public-body or federal technical accessibility certification.** Québec's government website standard and federal accessibility legislation have specified coverage, not universal application to all private sites. General discrimination/accommodation duties are a separate issue. Keep keyboard, focus, contrast, headings, and link-name checks and a way to report problems. No rendered accessibility audit was conducted for this research. [Québec website standard](https://www.quebec.ca/gouvernement/ministeres-organismes/cybersecurite-numerique/publications/standard-accessibilite-sites-web), [Federal act coverage](https://www.canada.ca/en/employment-social-development/programs/accessible-canada/act-summary.html), [Québec human-rights Charter](https://www.legisquebec.gouv.qc.ca/en/document/cs/C-12).

## Proposed follow-up order

1. Use the confirmed personal-hobby status for any focused legal/regulator scope assessment. Treat independent public API use as current scope and resolve downstream rights before promoting reuse.
2. Inspect effective deployed logging and provider settings without copying visitor records or secrets into research notes. Establish retention and processing locations.
3. Revise the #415 proposal for all logging channels, accurate rate-limiter wording, administrative processing, the TMDB notice, and applicable rights/governance disclosures. This research does not approve final copy.
4. Preserve the separately accepted Cineplex and Cinémathèque decisions. Inventory synopsis/image provenance and downstream reuse rights without representing accepted risks as permission.
5. Complete #410 with expiry behavior during failures. If Québec enterprise rules apply, establish proportionate privacy procedures and French-language coverage as separate work.
6. Run normal code, accessibility, review, and delivery checks only when implementation is authorized. No research result here authorizes deployment or removal of draft labels.

## Remaining facts to establish

- Which human editors/administrators have accounts, and which auth/audit features are live?
- Which database, Auth project, alias-routing service, log destinations, backup arrangements, processing regions, and provider agreements are active? Gmail is confirmed as the destination mailbox.
- What retention, deletion, request-handling, incident, and privacy-assessment procedures already exist?
- Are there permissions or agreements for cinema descriptions/images and Cinémathèque access that were not available to this research?

## Limits and maintenance

This review checked public primary sources and repository evidence. It did not determine contract formation, enforceability, ownership of particular images, enterprise status, actual production data flows, or every foreign jurisdiction. Some official pages returned 403/502 or were unavailable. The language analysis distinguishes current legislation from dated OQLF interpretive material; no inaccessible statutory exception is treated as settled.

Keep this as a dated engineering research record. Approved public copy belongs in the implementation linked to #415; durable settled decisions can later enter Atlas through its review process. Recheck sources and production facts when those changes are reviewed.
