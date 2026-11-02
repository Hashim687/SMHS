from django.core.management.base import BaseCommand

from clinic.models import Department, LabTest, Location, Symptom, TicketPrice, TriageRule

DEPTS = """GENMED|General Medicine|جنرل میڈیسن|
CARDIO|Cardiology|امراضِ قلب|
GASTRO|Gastroenterology|معدہ و جگر|
NEURO|Neurology|اعصابی امراض|
ORTHO|Orthopaedics|ہڈی و جوڑ|
PULMO|Pulmonology|امراضِ سینہ|
ENT|ENT|ناک کان گلا|
OPHTH|Ophthalmology|آنکھ|
DERM|Dermatology|جلدی امراض|
GYNAE|Gynaecology|امراضِ نسواں|
UROLOGY|Urology|گردہ و مثانہ|
PAED|Paediatrics|بچوں کے امراض|
GENSURG|General Surgery|جنرل سرجری|
EMERG_MED|Medical Emergency|میڈیکل ایمرجنسی|medical
EMERG_SURG|Surgical Emergency|سرجیکل ایمرجنسی|surgical"""

SYMS = """fever|🤒||0|GENMED2
cough|😷||0|PULMO2,GENMED1,ENT1
breathless|😮‍💨|medical|2|PULMO2,CARDIO1
chest_pain|🫀|medical|3|CARDIO3
palpitations|💓|medical|1|CARDIO2
headache|🤕||0|NEURO2,GENMED1
dizziness|😵‍💫||0|NEURO1,GENMED1,ENT1
seizure|⚡|medical|3|NEURO3
unconscious|😵|medical|3|NEURO2,GENMED2
weak_one_side|🧠|medical|3|NEURO3
abdominal_pain|🤢|surgical|1|GASTRO2,GENSURG1
vomiting|🤮|medical|1|GASTRO2,GENMED1
blood_vomit|🩸|medical|3|GASTRO3
diarrhea|🚽|medical|1|GASTRO2
rectal_bleeding|🩸|surgical|2|GASTRO2,GENSURG2
joint_pain|🦵||0|ORTHO3
back_pain|🧍||0|ORTHO2,NEURO1
fracture|🦴|surgical|2|ORTHO3
injury|🤕|surgical|2|GENSURG1,ORTHO1
head_injury|🤕|surgical|3|NEURO2,GENSURG1
burns|🔥|surgical|3|GENSURG2
bleeding|🩸|surgical|3|GENSURG2
rash|🔴||0|DERM3
eye_pain|👁️||0|OPHTH3
ear_pain|👂||0|ENT3
sore_throat|🗣️||0|ENT3,GENMED1
pregnancy|🤰||0|GYNAE3
urinary|💧||0|UROLOGY3
poisoning|☠️|medical|3|GENMED1"""


LOCS = """CASHIER|Cashier Counter, Ground Floor|کیشیئر کاؤنٹر، گراؤنڈ فلور
SAMPLE|Sample Collection Room, Lab|سیمپل کلیکشن روم، لیب
REPORT|Report Counter, Lab|رپورٹ کاؤنٹر، لیب
XRAY|Radiology Reception|ریڈیالوجی استقبالیہ"""

TESTS = """HB|Haemoglobin|ہیموگلوبن|g/dL|12|17.5|60
FBS|Fasting Blood Sugar|فاسٹنگ بلڈ شوگر|mg/dL|70|100|45
CREAT|Serum Creatinine|سیرم کریٹینین|mg/dL|0.6|1.3|60
CHOL|Total Cholesterol|کل کولیسٹرول|mg/dL||200|60
NA|Serum Sodium|سیرم سوڈیم|mmol/L|135|145|45
K|Serum Potassium|سیرم پوٹاشیم|mmol/L|3.5|5.1|45
TSH|TSH|ٹی ایس ایچ|mIU/L|0.4|4|120
URINE|Urine Routine|پیشاب معائنہ||||45
ECG|ECG|ای سی جی||||20
CXR|Chest X-ray|سینے کا ایکسرے||||30"""


class Command(BaseCommand):
    def handle(self, *a, **k):
        for line in DEPTS.splitlines():
            c, en, ur, cat = line.split("|")
            Department.objects.update_or_create(code=c, defaults={"name_en": en, "name_ur": ur, "emergency_category": cat})
        for kind in ("opd", "emergency"):
            TicketPrice.objects.get_or_create(kind=kind, defaults={"amount": 10})
        for line in SYMS.splitlines():
            key, icon, cat, sev, rules = line.split("|")
            s, _ = Symptom.objects.update_or_create(key=key, defaults={"icon": icon, "emergency_category": cat, "severity": int(sev)})
            for r in rules.split(","):
                TriageRule.objects.update_or_create(symptom=s, department=Department.objects.get(code=r[:-1]), defaults={"weight": int(r[-1])})
        L = {}
        for line in LOCS.splitlines():
            c, en, ur = line.split("|")
            L[c], _ = Location.objects.update_or_create(code=c, defaults={"name_en": en, "name_ur": ur})
        for line in TESTS.splitlines():
            c, en, ur, unit, lo, hi, tat = line.split("|")
            rep = L["XRAY"] if c == "CXR" else L["REPORT"]
            d = {"name_en": en, "name_ur": ur, "unit": unit, "ref_low": lo or None, "ref_high": hi or None, "turnaround_minutes": int(tat),
                 "pay_at": L["CASHIER"], "sample_at": L["XRAY"] if c in ("CXR", "ECG") else L["SAMPLE"], "report_at": rep}
            LabTest.objects.update_or_create(code=c, defaults=d, create_defaults={**d, "price": 50})
