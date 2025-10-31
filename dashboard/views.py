from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from dashboard.models import District, MgnregaRecord
import requests


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
