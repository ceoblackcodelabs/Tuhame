# apps/report/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class ReportType(models.TextChoices):
    DAILY = 'daily', 'Daily Report'
    WEEKLY = 'weekly', 'Weekly Report'
    MONTHLY = 'monthly', 'Monthly Report'
    YEARLY = 'yearly', 'Yearly Report'
    CUSTOM = 'custom', 'Custom Report'


class ReportStatus(models.TextChoices):
    GENERATING = 'generating', 'Generating'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Report(models.Model):
    """Model to store generated reports"""
    report_id = models.CharField(max_length=50, unique=True)
    report_type = models.CharField(max_length=20, choices=ReportType.choices, default=ReportType.DAILY)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Report Period
    start_date = models.DateField()
    end_date = models.DateField()
    generated_for_date = models.DateField(null=True, blank=True)  # For daily reports

    # Report Content (JSON store for structured data)
    report_data = models.JSONField(default=dict, blank=True)

    # File Storage (for PDF/Excel exports)
    pdf_file = models.FileField(upload_to='reports/pdf/', blank=True, null=True)
    excel_file = models.FileField(upload_to='reports/excel/', blank=True, null=True)

    # Statistics Summary
    total_properties = models.IntegerField(default=0)
    total_clients = models.IntegerField(default=0)
    total_contracts = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_invoices = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overdue_invoices = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Metadata
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.GENERATING)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    # Report Parameters (store filter criteria)
    parameters = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['report_id']),
            models.Index(fields=['report_type', 'generated_at']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['generated_by', 'generated_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.report_id:
            self.report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class ReportSchedule(models.Model):
    """Model for scheduling automatic reports"""
    SCHEDULE_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    name = models.CharField(max_length=100)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES)
    is_active = models.BooleanField(default=True)
    recipients = models.JSONField(default=list)  # List of email addresses
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.schedule_type})"