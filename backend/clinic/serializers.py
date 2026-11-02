from rest_framework import serializers

from .models import Department, Ticket


class TicketCreate(serializers.Serializer):
    kind = serializers.ChoiceField(["opd", "emergency"])
    name = serializers.CharField(min_length=2, max_length=80, trim_whitespace=True)
    phone = serializers.RegexField(r"^[6-9]\d{9}$")
    age = serializers.IntegerField(min_value=0, max_value=120)
    sex = serializers.ChoiceField(["m", "f", "o"])
    language = serializers.ChoiceField(["en", "ur", "ks"], default="en")


class DeptOut(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["code", "name_en", "name_ur", "name_ks"]


def summary(t):
    a = t.admissions.order_by("-id").first()
    return {"status": t.status, "kind": t.kind, "patient_uid": t.patient.uid if t.patient else None,
            "triaged": bool(t.triaged_at), "department": DeptOut(t.department).data if t.department else None,
            "token_no": t.token_no, "category": t.category, "priority": t.priority, "escalate": t.escalate, "state": t.state,
            "admission": {"status": a.status, "ward": a.ward} if a else None}
