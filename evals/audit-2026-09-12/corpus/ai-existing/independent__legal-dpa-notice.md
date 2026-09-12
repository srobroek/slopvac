# Data Processing and Subprocessor Notice

**Product:** Hosted Log Analytics Service
**Notice version:** 4.2
**Effective date:** 1 September 2026
**Supersedes:** Notice version 4.1 (effective 3 March 2026)

This Notice forms part of the Data Processing Addendum ("DPA") incorporated by reference into the Master Subscription Agreement between the Customer and the Vendor. In the event of a conflict between this Notice and the DPA, the DPA prevails. Capitalised terms not defined herein bear the meaning given in the DPA or, where not defined there, in Regulation (EU) 2016/679 ("GDPR").

## 1. Roles of the Parties

For all Customer Data ingested into the Service, the Customer acts as Controller and the Vendor acts as Processor. Where the Customer is itself a Processor acting on behalf of a third-party Controller, the Vendor acts as Subprocessor and the Customer warrants that it holds the authority required to appoint the Vendor in that capacity.

The Vendor acts as Controller solely in respect of Account Data described in section 2(c), and processes such data for the purposes of contract administration, billing, and service security.

## 2. Categories of Personal Data Processed

(a) **Log Payload Data.** Personal data contained within log events, metrics, and traces transmitted to the Service by or at the direction of the Customer. The Vendor does not determine the content of such data. Categories may include IP addresses, device and session identifiers, user identifiers, request URLs, HTTP headers, user-agent strings, and any free-text values written by the Customer's applications.

(b) **Service Telemetry.** Query strings, dashboard configurations, alert definitions, and audit records identifying the Authorised User who performed each action, together with timestamp and source IP address.

(c) **Account Data.** Name, business email address, business telephone number, job title, authentication credentials, and billing contact details of Authorised Users and account administrators.

## 3. Retention Periods

| Data category | Retention period | Deletion mechanism |
| --- | --- | --- |
| Log Payload Data (hot tier) | As configured by Customer, 3 to 90 days | Automated expiry on index rollover |
| Log Payload Data (archive tier) | As configured by Customer, up to 24 months | Automated object lifecycle deletion |
| Service Telemetry | 13 months from event date | Automated expiry |
| Account Data | Term of the Agreement plus 90 days | Deletion on account closure |
| Backups containing any of the above | 35 days from snapshot creation | Automated snapshot rotation |

Upon termination or expiry of the Agreement, the Vendor deletes or returns all Customer Data within 30 days, save where retention is required by applicable law. Backup copies are purged in accordance with the rotation schedule stated above.

## 4. Authorised Subprocessors

| Subprocessor | Function | Processing location |
| --- | --- | --- |
| Amazon Web Services, Inc. | Compute, object storage, managed databases | Ireland (eu-west-1), Germany (eu-central-1), United States (us-east-1) |
| Cloudflare, Inc. | Edge ingestion, DDoS mitigation, TLS termination | Global edge network; EU-only routing available on request |
| Twilio SendGrid, Inc. | Transactional and alert email delivery | United States |
| Stripe Payments Europe, Ltd. | Payment processing for Account Data only | Ireland, United States |
| Zendesk, Inc. | Support ticketing and correspondence | European Union |

Transfers from the European Economic Area, Switzerland, and the United Kingdom to subprocessors outside those territories are made under the European Commission Standard Contractual Clauses (Decision 2021/914), supplemented by the UK International Data Transfer Addendum where applicable, together with the technical and organisational measures set out in Annex II of the DPA.

## 5. Customer Obligations

The Customer shall:

1. Establish a lawful basis for all processing instructed under the Agreement.
2. Provide all notices and obtain all consents required from Data Subjects.
3. Refrain from transmitting special category data within the meaning of Article 9 GDPR, payment card data, or government identification numbers into log payloads. Redaction and masking controls are made available in the Service for this purpose; configuration of those controls is the Customer's responsibility.
4. Configure retention periods consistent with its own data minimisation obligations.
5. Respond to Data Subject requests as Controller, using the export and deletion interfaces provided by the Service.

The Vendor bears no liability for personal data transmitted into the Service in contravention of paragraph 3 above.

## 6. Objection to New Subprocessors

The Vendor will publish notice of any intended addition or replacement of a subprocessor at least 30 calendar days before that subprocessor begins processing Customer Data. Notice is given by email to the account administrator of record and by revision of this page.

The Customer may object on reasonable data protection grounds by submitting written notice to privacy@vendor.example within 20 calendar days of publication, stating the grounds of objection. The Vendor will use reasonable efforts to make available a change in configuration or an alternative arrangement that avoids the objected processing. Where no such arrangement can be made available within 30 days of the objection, the Customer may terminate the affected subscription on written notice, with a pro-rata refund of prepaid fees for the unexpired term.

Absence of a timely objection constitutes approval of the subprocessor.

## 7. Contact

Data Protection Officer, privacy@vendor.example. EU representative appointed under Article 27 GDPR: details available on request.
