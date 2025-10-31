from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from dashboard.models import District, MgnregaRecord
import requests, json


def index(request):
    """Show all Gujarat districts."""
    districts = District.objects.filter(state_name__iexact="GUJARAT").order_by("district_name")
    return render(request, "index.html", {"districts": districts})


def detect_district_from_location(lat, lon):
    """Detect district name using OpenStreetMap reverse geocoding."""
    try:
        res = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 6, "addressdetails": 1},
            headers={"User-Agent": "mgnrega-dashboard"},
            timeout=10,
        )
        if res.status_code == 200:
            data = res.json()
            addr = data.get("address", {})
            return addr.get("district") or addr.get("state_district")
    except Exception:
        return None
    return None


def district_detail(request, district_code):
    """Render district dashboard with all MGNREGA indicators."""
    district = get_object_or_404(District, district_code=district_code)
    records = district.records.all().order_by("fin_year", "month")

    data = [
        {
            "fin_year": r.fin_year,
            "month": r.month,
            "total_exp_lakhs": r.total_exp_lakhs or 0,
            "wages_lakhs": r.wages_lakhs or 0,
            "total_jobcards_issued": r.total_jobcards_issued or 0,
            "total_active_job_cards": r.total_active_job_cards or 0,
            "total_active_workers": r.total_active_workers or 0,
            "total_workers": r.total_workers or 0,
            "total_households": r.total_households or 0,
            "total_individuals": r.total_individuals or 0,
        }
        for r in records
    ]
    return render(request, "district.html", {"district": district, "records": data})


@require_GET
def district_records_api(request, district_code):
    """Return all indicators as JSON (for frontend charts)."""
    district = get_object_or_404(District, district_code=district_code)
    records = district.records.all().order_by("fin_year", "month")

    data = [
        {
            "fin_year": r.fin_year,
            "month": r.month,
            "total_exp_lakhs": r.total_exp_lakhs or 0,
            "wages_lakhs": r.wages_lakhs or 0,
            "total_jobcards_issued": r.total_jobcards_issued or 0,
            "total_active_job_cards": r.total_active_job_cards or 0,
            "total_active_workers": r.total_active_workers or 0,
            "total_workers": r.total_workers or 0,
            "total_households": r.total_households or 0,
            "total_individuals": r.total_individuals or 0,
        }
        for r in records
    ]
    return JsonResponse({"district": district.district_name, "data": data})


# ✅ NEW: Frontend → Backend sync endpoint
@csrf_exempt
def save_records(request, district_code):
    """Accepts POSTed JSON data from frontend and stores it in DB."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        body = json.loads(request.body)
        records = body.get("records", [])
        district = get_object_or_404(District, district_code=district_code)
        saved = 0

        for item in records:
            MgnregaRecord.objects.update_or_create(
                district=district,
                fin_year=item.get("fin_year"),
                month=item.get("month"),
                defaults={
                    "total_exp_lakhs": item.get("Total_Exp"),
                    "wages_lakhs": item.get("Wages"),
                    "total_jobcards_issued": item.get("Total_No_of_JobCards_issued"),
                    "total_active_job_cards": item.get("Total_No_of_Active_Job_Cards"),
                    "total_active_workers": item.get("Total_No_of_Active_Workers"),
                    "total_workers": item.get("Total_No_of_Workers"),
                    "total_households": item.get("Total_Households_Worked"),
                    "total_individuals": item.get("Total_Individuals_Worked"),
                    "raw": item,
                    "fetched_at": timezone.now(),
                },
            )
            saved += 1

        return JsonResponse({"status": "ok", "saved": saved})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
