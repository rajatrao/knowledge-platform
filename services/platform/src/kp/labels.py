"""Display labels. Counts are never stored here."""

from __future__ import annotations

THEME_LABELS = {
    "installation_delays": "Installation Delays",
    "battery_performance": "Battery Performance",
    "billing_confusion": "Billing Confusion",
    "app_problems": "App Problems",
    "communication_problems": "Communication Problems",
}

CAUSE_LABELS = {
    "permitting_delays": "Permitting delays",
    "installer_scheduling": "Installer scheduling",
    "customer_communication": "Customer communication",
    "capacity_below_spec": "Capacity below spec",
    "backup_duration": "Backup duration",
    "charge_rate": "Charge rate",
    "rate_plan": "Rate plan",
    "invoice_timing": "Invoice timing",
    "credit_application": "Credit application",
    "login": "Login",
    "telemetry_display": "Telemetry display",
    "notifications": "Notifications",
    "status_updates": "Status updates",
    "scheduling_calls": "Scheduling calls",
    "unclear_next_steps": "Unclear next steps",
    "other": "Other",
}

BLOCKER_LABELS = {
    "permitting": "Permitting",
    "installer_capacity": "Installer capacity",
    "customer_scheduling": "Customer scheduling",
}

BLOCKER_CAUSE = {
    "permitting": "permitting_delays",
    "installer_capacity": "installer_scheduling",
    "customer_scheduling": "customer_communication",
}

TECHNICAL_LABELS = {
    "battery_telemetry": "Battery telemetry",
    "mobile_app": "Mobile app",
    "firmware": "Firmware",
}

VALUE_LABELS = {
    "energy_independence": "Energy independence",
    "installation_experience": "Installation experience",
    "battery_reliability": "Battery reliability",
}

SAMPLE_QUESTIONS = {
    "ceo": "What are the top customer complaints and recommended solutions?",
    "operations_manager": "Which operational problems are driving customer complaints?",
    "engineer": "Which customer complaints appear related to technical incidents?",
    "marketing": "What language are customers using when they describe why they value Base Power?",
}

PERSONA_SKILLS = {
    "ceo": "customer-complaints",
    "operations_manager": "complaint-drivers",
    "engineer": "complaint-incidents",
    "marketing": "value-language",
}

ROLES = ("ceo", "operations_manager", "engineer", "marketing")
