from django.core.management.base import BaseCommand
from django.db import transaction
from hmis.models import IndicatorMetadata

class Command(BaseCommand):
    help = "Automatically classify HMIS indicators into group, domain, short name, and sort order."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview classification without saving changes",
        )
        parser.add_argument(
            "--only-empty",
            action="store_true",
            help="Only classify records where group/domain/short name are empty",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        only_empty = options["only_empty"]

        qs = IndicatorMetadata.objects.all().order_by("indicator_name")

        total = qs.count()
        updated = 0
        skipped = 0

        if total == 0:
            self.stdout.write(self.style.WARNING("No IndicatorMetadata records found."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {total} indicator metadata records."))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run mode enabled. No changes will be saved."))

        with transaction.atomic():
            for obj in qs:
                if only_empty:
                    already_classified = any([
                        obj.indicator_group,
                        obj.indicator_domain,
                        obj.indicator_short_name,
                        obj.sort_order is not None,
                    ])
                    if already_classified:
                        skipped += 1
                        continue

                classification = classify_indicator(obj.indicator_name)

                changed = False

                if classification["indicator_group"] != obj.indicator_group:
                    obj.indicator_group = classification["indicator_group"]
                    changed = True

                if classification["indicator_domain"] != obj.indicator_domain:
                    obj.indicator_domain = classification["indicator_domain"]
                    changed = True

                if classification["indicator_short_name"] != obj.indicator_short_name:
                    obj.indicator_short_name = classification["indicator_short_name"]
                    changed = True

                if classification["sort_order"] != obj.sort_order:
                    obj.sort_order = classification["sort_order"]
                    changed = True

                if changed:
                    updated += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"UPDATED: {obj.indicator_name} | "
                            f"group={obj.indicator_group} | "
                            f"domain={obj.indicator_domain} | "
                            f"short={obj.indicator_short_name} | "
                            f"sort={obj.sort_order}"
                        )
                    )
                    if not dry_run:
                        obj.save()
                else:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(f"SKIPPED: {obj.indicator_name} (no change)")
                    )

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Classification completed."))
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated}"))
        self.stdout.write(self.style.WARNING(f"Skipped: {skipped}"))


def classify_indicator(indicator_name: str) -> dict:
    name = (indicator_name or "").strip()

    mapping = {
        "ANC1": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Antenatal Care",
            "indicator_short_name": "ANC1",
            "sort_order": 1,
        },
        "ANC2": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Antenatal Care",
            "indicator_short_name": "ANC2",
            "sort_order": 2,
        },
        "ANC3": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Antenatal Care",
            "indicator_short_name": "ANC3",
            "sort_order": 3,
        },
        "ANC4": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Antenatal Care",
            "indicator_short_name": "ANC4",
            "sort_order": 4,
        },
        "ANC-Other": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Antenatal Care",
            "indicator_short_name": "ANC Other",
            "sort_order": 5,
        },
        "A-delivery": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Delivery Care",
            "indicator_short_name": "Assisted Delivery",
            "sort_order": 10,
        },
        "N-delivery": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Delivery Care",
            "indicator_short_name": "Normal Delivery",
            "sort_order": 11,
        },
        "C-Section": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Delivery Care",
            "indicator_short_name": "C-Section",
            "sort_order": 12,
        },
        "Uterotonic-third-stage-labor": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Delivery Care",
            "indicator_short_name": "Uterotonic 3rd Stage",
            "sort_order": 13,
        },
        "PNC1": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Postnatal Care",
            "indicator_short_name": "PNC1",
            "sort_order": 20,
        },
        "PNC2": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Postnatal Care",
            "indicator_short_name": "PNC2",
            "sort_order": 21,
        },
        "PNC-Other": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "Postnatal Care",
            "indicator_short_name": "PNC Other",
            "sort_order": 22,
        },
        "OPD-NewPatients-Clients": {
            "indicator_group": "Service Utilization",
            "indicator_domain": "General Service Utilization",
            "indicator_short_name": "OPD New Clients",
            "sort_order": 30,
        },
        "APH": {
            "indicator_group": "Maternal Complications",
            "indicator_domain": "Maternal Complications",
            "indicator_short_name": "APH",
            "sort_order": 40,
        },
        "PPH": {
            "indicator_group": "Maternal Complications",
            "indicator_domain": "Maternal Complications",
            "indicator_short_name": "PPH",
            "sort_order": 41,
        },
        "Pre-eclampsia": {
            "indicator_group": "Maternal Complications",
            "indicator_domain": "Maternal Complications",
            "indicator_short_name": "Pre-eclampsia",
            "sort_order": 42,
        },
        "Eclampsia": {
            "indicator_group": "Maternal Complications",
            "indicator_domain": "Maternal Complications",
            "indicator_short_name": "Eclampsia",
            "sort_order": 43,
        },
        "Asphyxia": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Asphyxia",
            "sort_order": 50,
        },
        "Babies-breastfed-1st-hour": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Breastfed 1st Hour",
            "sort_order": 51,
        },
        "LBW": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "LBW",
            "sort_order": 52,
        },
        "Newborn-resuscitated": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "NB Resuscitated",
            "sort_order": 53,
        },
        "NewbornAlive": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Newborn Alive",
            "sort_order": 54,
        },
        "Premature": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Premature",
            "sort_order": 55,
        },
        "Sepsis": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Sepsis",
            "sort_order": 56,
        },
        "Stillbirth": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Stillbirth",
            "sort_order": 57,
        },
        "StillbirthFresh": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Fresh Stillbirth",
            "sort_order": 58,
        },
        "StillbirthRotten": {
            "indicator_group": "Newborn Outcomes",
            "indicator_domain": "Newborn Outcomes",
            "indicator_short_name": "Macerated Stillbirth",
            "sort_order": 59,
        },
    }

    default_value = {
        "indicator_group": "Other",
        "indicator_domain": "Other",
        "indicator_short_name": name,
        "sort_order": 999,
    }

    return mapping.get(name, default_value)