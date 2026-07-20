"""
Fraud pattern knowledge base. Owner: Member C

The documents seeded into ChromaDB for RAG retrieval. Each entry is one fraud
pattern described the way an analyst would recognise it, so semantic search on
transaction features surfaces the right patterns.
"""

FRAUD_PATTERNS: list[dict] = [
    # ── Synthetic identity ────────────────────────────────────────────────────
    {"id": "p01", "type": "synthetic_identity", "text": "Synthetic identity fraud: multiple accounts sharing the same device fingerprint or IP address, often created in rapid succession with slightly varied personal information."},
    {"id": "p02", "type": "synthetic_identity", "text": "Synthetic identity incubation: a fabricated identity makes small regular transactions for months to build a credible history before being used for large-value fraud."},
    {"id": "p03", "type": "synthetic_identity", "text": "Identity cluster tell: several accounts with different names but identical behavioural fingerprints — same device model, same login hours, same merchant mix — indicating one operator behind many identities."},

    # ── Money mule networks ───────────────────────────────────────────────────
    {"id": "p04", "type": "money_mule", "text": "Money mule network: circular transaction flows between 3-5 accounts where funds originate and return to the same source account within hours."},
    {"id": "p05", "type": "money_mule", "text": "Mule fee skimming: funds pass through a chain of accounts with each hop forwarding 85-95% of the amount received, the remainder kept as the mule's cut. Amounts that shrink hop-by-hop are the signature."},
    {"id": "p06", "type": "money_mule", "text": "Recruited mule onboarding: a dormant personal account suddenly starts receiving mid-size transfers from strangers and forwarding them within minutes, often to wire or crypto endpoints."},

    # ── Account takeover ──────────────────────────────────────────────────────
    {"id": "p07", "type": "account_takeover", "text": "Account takeover: sudden spike in transaction velocity from a single account with unusual merchant categories and new device fingerprints not seen in account history."},
    {"id": "p08", "type": "account_takeover", "text": "Post-takeover drain: immediately after a credential change or new device login, the account sends its full balance to a never-before-seen recipient, often via wire transfer."},
    {"id": "p09", "type": "account_takeover", "text": "Takeover staging: attacker first makes a tiny test payment to a controlled account to confirm access, then follows with the real drain transaction within the hour."},

    # ── Wire fraud ────────────────────────────────────────────────────────────
    {"id": "p10", "type": "wire_fraud", "text": "Wire fraud: large wire transfers to new recipient accounts in high-risk jurisdictions, often preceded by social engineering and followed by rapid fund movement."},
    {"id": "p11", "type": "wire_fraud", "text": "Urgency-driven wire: a customer who has never wired money before suddenly sends an amount several times their monthly average, characteristic of a scammer applying time pressure."},
    {"id": "p12", "type": "wire_fraud", "text": "Wire smokescreen: a large outbound wire split across two or three same-day transfers to related recipients to stay under review thresholds."},

    # ── Card-not-present ──────────────────────────────────────────────────────
    {"id": "p13", "type": "cnp_fraud", "text": "Card-not-present fraud: multiple small test transactions followed by one large transaction, typically across e-commerce and crypto exchange merchants."},
    {"id": "p14", "type": "cnp_fraud", "text": "Card testing burst: dozens of sub-$5 authorizations in minutes against online merchants, used to validate stolen card numbers before resale or cash-out."},
    {"id": "p15", "type": "cnp_fraud", "text": "Cross-border CNP anomaly: online purchases from an IP geolocation far from the cardholder's home country with shipping to a freight forwarder address."},

    # ── Friendly fraud / disputes ─────────────────────────────────────────────
    {"id": "p16", "type": "friendly_fraud", "text": "Friendly fraud: dispute patterns where a customer regularly initiates chargebacks after transactions with online merchants, particularly in gaming and digital goods."},
    {"id": "p17", "type": "friendly_fraud", "text": "Serial disputer: an account whose chargeback-to-purchase ratio exceeds 10%, repeatedly claiming non-delivery on digital goods that logs show were consumed."},

    # ── Bust-out ──────────────────────────────────────────────────────────────
    {"id": "p18", "type": "bust_out", "text": "Bust-out fraud: account opens with small normal activity to build credit history, then suddenly maxes out all credit limits before becoming uncontactable."},
    {"id": "p19", "type": "bust_out", "text": "Coordinated bust-out ring: several linked accounts (shared device or address) all max their limits in the same week after months of minimal activity."},

    # ── Laundering ────────────────────────────────────────────────────────────
    {"id": "p20", "type": "laundering", "text": "Transaction laundering: legitimate-looking merchant processes transactions on behalf of undisclosed high-risk merchants, obscuring true nature of payments."},
    {"id": "p21", "type": "laundering", "text": "Layering pattern: funds move rapidly through a series of accounts and instruments — wire to crypto to prepaid cards — with no economic purpose other than obscuring origin."},
    {"id": "p22", "type": "laundering", "text": "Funnel account: many small deposits from unrelated senders in different regions consolidated into one account, then withdrawn or wired out in a single large transaction."},

    # ── Structuring / smurfing ────────────────────────────────────────────────
    {"id": "p23", "type": "structuring", "text": "Structuring (smurfing): deposits or transfers deliberately kept just below the 10,000 reporting threshold, e.g. repeated 9,000-9,900 transactions over consecutive days."},
    {"id": "p24", "type": "structuring", "text": "Distributed structuring: one beneficiary receiving just-below-threshold amounts from several coordinated senders on the same day."},

    # ── Phishing / authorized push payment ────────────────────────────────────
    {"id": "p25", "type": "app_scam", "text": "Authorized push payment scam: victim is socially engineered into sending money themselves, typically an urgent transfer to a 'safe account' or fake bank representative."},
    {"id": "p26", "type": "app_scam", "text": "Impersonation scam payment: transfer to a newly created account shortly after the victim received calls or messages impersonating a bank, tax agency, or police."},
    {"id": "p27", "type": "app_scam", "text": "Invoice redirection: a regular supplier payment suddenly routed to different bank details after an email requesting the change, classic business email compromise outcome."},

    # ── Romance scams ─────────────────────────────────────────────────────────
    {"id": "p28", "type": "romance_scam", "text": "Romance scam remittance: escalating transfers from an older account holder to an overseas recipient they have never transacted with before, often framed as emergencies."},
    {"id": "p29", "type": "romance_scam", "text": "Romance scam progression: transfers that start small and grow steadily over weeks to the same foreign beneficiary, frequently via wire or crypto purchase."},

    # ── BEC / invoice fraud ───────────────────────────────────────────────────
    {"id": "p30", "type": "bec", "text": "Business email compromise: corporate account sends an unusual high-value wire to a first-time beneficiary, initiated outside normal business hours or approval flow."},
    {"id": "p31", "type": "bec", "text": "CEO fraud: urgent wire requested at quarter-end or before a holiday weekend to a new international beneficiary, bypassing normal dual-approval controls."},
    {"id": "p32", "type": "bec", "text": "Vendor impersonation: payment to an account whose name closely resembles a known supplier but with different banking details and a recently registered lookalike domain."},

    # ── Payroll diversion ─────────────────────────────────────────────────────
    {"id": "p33", "type": "payroll_diversion", "text": "Payroll diversion: an employee's direct deposit details changed shortly before payday, rerouting salary to a prepaid card or mule account."},

    # ── Crypto ────────────────────────────────────────────────────────────────
    {"id": "p34", "type": "crypto_fraud", "text": "Crypto off-ramp: fraud proceeds converted quickly through a crypto exchange purchase, typically a first-ever crypto transaction for the account at an unusual amount."},
    {"id": "p35", "type": "crypto_fraud", "text": "Pig butchering: victim makes escalating transfers to a fake investment platform, often starting small with a staged 'withdrawal' allowed early to build trust."},
    {"id": "p36", "type": "crypto_fraud", "text": "Crypto mixer hop: funds sent to an exchange, converted, and moved to a mixing service within hours — velocity between fiat and mixer is the key indicator."},

    # ── Elder financial abuse ─────────────────────────────────────────────────
    {"id": "p37", "type": "elder_abuse", "text": "Elder financial abuse: sudden change in a long-stable senior account — new payees, ATM bursts, or large transfers coinciding with a new caregiver or 'advisor'."},
    {"id": "p38", "type": "elder_abuse", "text": "Grandparent scam: an urgent wire or gift card purchase by a senior account holder following a call claiming a family member is in legal or medical trouble."},

    # ── Gift cards ────────────────────────────────────────────────────────────
    {"id": "p39", "type": "gift_card_scam", "text": "Gift card cash-out: repeated same-day purchases of high-denomination gift cards, the preferred untraceable payment demanded by phone scammers."},
    {"id": "p40", "type": "gift_card_scam", "text": "Gift card laundering: stolen card credentials used to buy digital gift cards that are resold on secondary markets within minutes of purchase."},

    # ── Refund fraud ──────────────────────────────────────────────────────────
    {"id": "p41", "type": "refund_fraud", "text": "Refund fraud: account receives merchant refunds that exceed its purchase history, indicating fake-return or refund-as-a-service abuse."},
    {"id": "p42", "type": "refund_fraud", "text": "Double-dip refund: customer receives a chargeback and a merchant refund for the same transaction, a pattern visible when refund credits follow dispute credits."},

    # ── Triangulation ─────────────────────────────────────────────────────────
    {"id": "p43", "type": "triangulation", "text": "Triangulation fraud: a fake storefront takes real customer orders, fulfils them using stolen cards on a legitimate retailer, and pockets the customer payment."},

    # ── Promotion abuse ───────────────────────────────────────────────────────
    {"id": "p44", "type": "promo_abuse", "text": "Promotion abuse: many new accounts from the same device or IP claiming sign-up bonuses or referral credits, then cashing out and going dormant."},
    {"id": "p45", "type": "promo_abuse", "text": "Referral ring: a closed loop of accounts referring each other to farm bonuses, detectable as a dense referral subgraph with no external activity."},

    # ── P2P payment scams ─────────────────────────────────────────────────────
    {"id": "p46", "type": "p2p_scam", "text": "P2P marketplace scam: buyer sends an instant e-transfer for goods that never arrive; the seller account collects several such payments then empties out."},
    {"id": "p47", "type": "p2p_scam", "text": "Accidental transfer recovery scam: fraudster 'accidentally' sends money from a stolen account and pressures the recipient to return it to a different account."},

    # ── Check fraud ───────────────────────────────────────────────────────────
    {"id": "p48", "type": "check_fraud", "text": "Check kiting: rapid transfers between accounts at different institutions exploiting float, keeping balances artificially inflated with circular cover deposits."},
    {"id": "p49", "type": "check_fraud", "text": "Fake check overpayment: deposit of a check followed immediately by wiring most of it back or onward before the check bounces."},

    # ── Credential / infrastructure attacks ───────────────────────────────────
    {"id": "p50", "type": "sim_swap", "text": "SIM swap takeover: authentication phone number ported to a new SIM followed within hours by password resets and high-value outbound transfers."},
    {"id": "p51", "type": "credential_stuffing", "text": "Credential stuffing wave: many failed logins across accounts from one IP range followed by small verification transactions on the accounts that succeeded."},
    {"id": "p52", "type": "bin_attack", "text": "BIN attack: sequential card numbers from one issuer BIN tested with small online authorizations, producing a burst of low-value declines and approvals."},

    # ── Miscellaneous social engineering ──────────────────────────────────────
    {"id": "p53", "type": "lottery_scam", "text": "Lottery/prize scam: victim sends 'fees' or 'taxes' via wire or money service to unlock fictitious winnings, often repeated with escalating amounts."},
    {"id": "p54", "type": "employment_scam", "text": "Fake job scam: new 'employee' receives a deposit and is told to buy equipment or forward funds to a supplier — turning the victim into an unwitting mule."},
    {"id": "p55", "type": "overpayment_scam", "text": "Overpayment scam: buyer sends more than the asking price then requests the difference refunded, with the original payment later reversed as fraudulent."},
    {"id": "p56", "type": "charity_fraud", "text": "Charity fraud spike: donation payments to a newly registered beneficiary that appears immediately after a disaster or crisis event."},
    {"id": "p57", "type": "real_estate_wire", "text": "Real estate closing scam: home purchase deposit wired to fraudster-supplied details after intercepted or spoofed closing instructions, typically a six-figure first-time wire."},
    {"id": "p58", "type": "loyalty_fraud", "text": "Loyalty point theft: sudden redemption or transfer of a large points balance following an account login from a new device, points converted to gift cards."},
]
