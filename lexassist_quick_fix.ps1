$ErrorActionPreference = "Stop"
Set-Location "D:\LexAssist"

$retrievalPath = "retrieval.py"
$appPath = "app.py"
$notificationPath = "data\processed\punjab_minimum_wages_notification_2025_sections.json"

if (!(Test-Path $retrievalPath) -or !(Test-Path $appPath)) {
    throw "Run this from the LexAssist project at D:\LexAssist; retrieval.py or app.py is missing."
}

# 1) Add the 2025 Pakistan-Punjab notification as a searchable, explicitly provisional record.
New-Item -ItemType Directory -Force -Path "data\processed" | Out-Null
$notification = @(
    @{
        act_name = "Punjab Minimum Wages Notification, 2025"
        year = 2025
        jurisdiction = "Punjab"
        document_type = "notification"
        section_number = "Notification (2025)"
        heading = "Minimum wage rates and permitted deductions"
        text = @"
Punjab Gazette Extraordinary, published Tuesday 9 September 2025. Government of the Punjab, Labour & Human Resource Department, notification dated Lahore 8 September 2025, No. SO(L&P) MW/2024, issued under section 6 of the Punjab Minimum Wages Act 2019 and stated to supersede the notification dated 5 September 2024. The copy states minimum rates for adult and adolescent workers in industrial and commercial establishments in Punjab effective 1 July 2025: Rs. 40,000 per month for 26 working days; Rs. 1,538.46 per day for eight working hours; Rs. 192.31 per hour. It also states permitted deductions by agreement for food (Rs. 100 per meal), transport (Rs. 1,800 per month), and accommodation (Rs. 2,000 per month); existing higher wages must not be reduced; employers may pay higher rates; and women must receive equal rates for work of equal value. IMPORTANT: this is a provisional reference-copy transcription. Official-source verification and whether a later notification supersedes it have not been confirmed. Do not treat these rates as verified current rates.
"@
        source_file = "data/raw_laws/punjab_minimum_wages_notification_2025_PROVISIONAL.pdf"
        source_url = "https://clr.org.pk/Labour-Laws/Minimum%20Wage%20Notification/Punjab.%20Minimum%20Wages%20Notification.%202025.pdf"
        jurisdiction_source_url = "https://punjablaws.punjab.gov.pk/"
        verification_status = "provisional_reference_copy_official_source_and_current_status_unverified"
        applicability = "Punjab notification; current legal status and supersession not verified"
    }
)
$notification | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $notificationPath

# 2) Ensure the notification JSON is included in retrieval's configured data files.
$retrieval = Get-Content $retrievalPath -Raw
if ($retrieval -notmatch [regex]::Escape("punjab_minimum_wages_notification_2025_sections.json")) {
    $match = [regex]::Match($retrieval, '(?s)DATA_PATHS\s*=\s*\[(.*?)\]')
    if (!$match.Success) { throw "Could not locate DATA_PATHS in retrieval.py; no code was changed there." }
    $newBlock = "DATA_PATHS = [`r`n" + $match.Groups[1].Value.TrimEnd() +
        "`r`n    Path(`"data/processed/punjab_minimum_wages_notification_2025_sections.json`"),`r`n]"
    $retrieval = $retrieval.Substring(0, $match.Index) + $newBlock + $retrieval.Substring($match.Index + $match.Length)
    Set-Content -Encoding utf8 $retrievalPath $retrieval
    Write-Host "Added notification JSON to retrieval.py."
} else {
    Write-Host "Notification JSON was already configured in retrieval.py."
}

# 3) Update the stale three-law UI warning to describe the expanded collection accurately.
$app = Get-Content $appPath -Raw
$warningPattern = '(?s)st\.warning\(\s*"Prototype limitation:.*?\n\)'
$warningReplacement = @'
st.warning(
    "Prototype limitation: the searchable collection includes eight law datasets "
    "and a provisional 2025 Punjab minimum-wage notification reference. The "
    "notification's official-source status and whether it has been superseded "
    "are unverified, so do not rely on its rates as current. Legal status, "
    "amendments, and section-specific applicability across the collection have "
    "not been fully verified. Check official sources before relying on a provision."
)
'@
if ($app -match $warningPattern) {
    $app = [regex]::Replace($app, $warningPattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $warningReplacement }, 1)
    Set-Content -Encoding utf8 $appPath $app
    Write-Host "Updated app.py collection warning."
} else {
    Write-Host "Could not safely match the old warning in app.py. Please inspect that warning manually."
}

# 4) Smoke-test loading and semantic retrieval for minimum wages, tenancy/property, and consumer law.
@'
from sentence_transformers import SentenceTransformer
from retrieval import load_sections, load_or_build_index, retrieve, MODEL_NAME

sections = load_sections()
print(f"\nLoaded searchable records: {len(sections)}")
notif = [s for s in sections if "minimum wages notification, 2025" in s.get("act_name", "").casefold()]
print(f"Notification records loaded: {len(notif)}")
if not notif:
    raise SystemExit("FAIL: minimum-wage notification is not in loaded corpus")

model = SentenceTransformer(MODEL_NAME)
index, documents = load_or_build_index(sections, model)
tests = [
    ("What minimum wage rates are stated in the 2025 Punjab notification?", "Punjab", "Punjab Minimum Wages Notification, 2025"),
    ("When does a lease of immovable property end?", "Punjab", "Transfer of Property Act"),
    ("What remedy is available for a defective consumer product?", "Punjab", "Punjab Consumer Protection Act"),
]
failed = False
for query, jurisdiction, expected in tests:
    results = retrieve(query, sections, model, index, documents, top_k=5, jurisdiction=jurisdiction)
    acts = [r["act_name"] for r in results]
    passed = any(expected.casefold() in act.casefold() for act in acts)
    print(f"\n{'PASS' if passed else 'CHECK'} | {query}\nTop results: {acts}")
    if not passed:
        failed = True
if failed:
    raise SystemExit("Some smoke tests did not return the expected Act in top 5; inspect printed results.")
print("\nAll smoke tests passed.")
'@ | python -
