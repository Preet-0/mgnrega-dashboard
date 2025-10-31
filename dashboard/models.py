from django.db import models


class District(models.Model):
    """Represents a single district within a state."""
    state_code = models.CharField(max_length=10, blank=True, null=True)
    state_name = models.CharField(max_length=200)
    district_code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    district_name = models.CharField(max_length=200)

    class Meta:
        ordering = ["state_name", "district_name"]

    def __str__(self):
        return f"{self.district_name} ({self.state_name})"


class MgnregaRecord(models.Model):
    """Stores monthly performance data for a district."""
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="records")

    # Time dimensions
    fin_year = models.CharField(max_length=50, blank=True, null=True)
    month = models.CharField(max_length=20, blank=True, null=True)

    # Key indicators (as seen in API)
    total_jobcards_issued = models.BigIntegerField(blank=True, null=True)
    total_active_job_cards = models.BigIntegerField(blank=True, null=True)
    total_active_workers = models.BigIntegerField(blank=True, null=True)
    total_workers = models.BigIntegerField(blank=True, null=True)
    total_households = models.BigIntegerField(blank=True, null=True)
    total_individuals = models.BigIntegerField(blank=True, null=True)

    total_exp_lakhs = models.FloatField(blank=True, null=True)  # Total_Exp (lakhs)
    wages_lakhs = models.FloatField(blank=True, null=True)      # Wages (lakhs)

    # Raw JSON snapshot
    raw = models.JSONField(blank=True, null=True)

    # Meta info
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["district", "-fetched_at"]
        unique_together = ("district", "fin_year", "month")
        indexes = [
            models.Index(fields=["district", "fin_year", "month"]),
        ]

    def __str__(self):
        return f"{self.district.district_name} — {self.month or ''} {self.fin_year or ''}"
