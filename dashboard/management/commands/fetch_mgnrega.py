import os
import time
import datetime
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from dashboard.models import District, MgnregaRecord

API_BASE = os.getenv("MGNREGA_API_BASE", "https://api.data.gov.in/resource/")
RESOURCE_ID = os.getenv("MGNREGA_RESOURCE_ID")
API_KEY = os.getenv("MGNREGA_API_KEY")


class Command(BaseCommand):
    help = "Fetch MGNREGA data for Gujarat and cache it in the local database (optimized bulk insert)."

    def handle(self, *args, **options):
        if not RESOURCE_ID or not API_KEY:
            self.stderr.write(self.style.ERROR("❌ Missing API key or resource ID! Check your .env file."))
            return

        url = f"{API_BASE.rstrip('/')}/{RESOURCE_ID}"
        params = {
            "api-key": API_KEY,
            "format": "json",
            "filters[state_name]": "GUJARAT",
            "limit": 50000,
        }

        retries = 3
        data = None

        for attempt in range(retries):
            try:
                res = requests.get(url, params=params, timeout=30)
                if res.status_code != 200:
                    self.stderr.write(f"⚠️ API status {res.status_code} (attempt {attempt+1})")
                    time.sleep(2 ** attempt)
                    continue
                data = res.json().get("records", [])
                break
            except Exception as e:
                self.stderr.write(f"⚠️ Fetch failed (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)

        if not data:
            self.stderr.write(self.style.WARNING("⚠️ API returned no records. Nothing saved."))
            return

        self.stdout.write(self.style.NOTICE(f"Fetched {len(data)} records. Saving to DB..."))

        # --- Helpers ---
        def to_float(v):
            try:
                return float(v)
            except Exception:
                return None

        def to_int(v):
            try:
                return int(float(v))
            except Exception:
                return None

        now = timezone.now()
        new_records = []

        # Fetch all existing (district, fin_year, month) combos to skip duplicates
        existing_keys = set(
            MgnregaRecord.objects.values_list("district_id", "fin_year", "month")
        )

        with transaction.atomic():
            for item in data:
                # --- Parse and clean basic fields ---
                state = (item.get("state_name") or "").strip().upper()
                district_name = (item.get("district_name") or "").strip().upper()
                if state != "GUJARAT" or not district_name:
                    continue

                # --- Parse period (month-year) ---
                period_str = (item.get("month") or "").strip()
                fin_year = (item.get("fin_year") or "").strip()
                month = None
                if period_str:
                    for fmt in ("%b-%Y", "%B-%Y", "%b %Y", "%B %Y"):
                        try:
                            dt = datetime.datetime.strptime(period_str, fmt)
                            month = dt.strftime("%B")
                            break
                        except ValueError:
                            continue

                # --- Get or create district ---
                district, _ = District.objects.get_or_create(
                    state_name=state,
                    district_name=district_name,
                    defaults={
                        "state_code": item.get("state_code", ""),
                        "district_code": item.get("district_code", ""),
                    },
                )

                key = (district.id, fin_year or "NA", month or period_str or "NA")
                if key in existing_keys:
                    continue  # skip duplicates
                existing_keys.add(key)

                # --- Build record object (not saving yet) ---
                rec = MgnregaRecord(
                    district=district,
                    fin_year=fin_year or "NA",
                    month=month or period_str or "NA",
                    total_jobcards_issued=to_int(item.get("Total_No_of_JobCards_issued")),
                    total_active_job_cards=to_int(item.get("Total_No_of_Active_Job_Cards")),
                    total_active_workers=to_int(item.get("Total_No_of_Active_Workers")),
                    total_exp_lakhs=to_float(item.get("Total_Exp")),
                    wages_lakhs=to_float(item.get("Wages")),
                    total_households=to_int(item.get("Total_Households_Worked")),
                    total_individuals=to_int(item.get("Total_Individuals_Worked")),
                    total_workers=to_int(item.get("Total_No_of_Workers")),
                    raw=item,
                    fetched_at=now,
                )
                new_records.append(rec)

        # --- Bulk insert all new records in one go ---
        if new_records:
            MgnregaRecord.objects.bulk_create(new_records, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"✅ Inserted {len(new_records)} new records successfully!"))
        else:
            self.stdout.write(self.style.WARNING("ℹ️ No new records to insert (already up-to-date)."))
