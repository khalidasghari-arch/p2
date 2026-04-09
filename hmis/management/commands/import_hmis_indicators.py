from django.core.management.base import BaseCommand
from django.db import connection, transaction

from hmis.models import IndicatorMetadata


class Command(BaseCommand):
    help = "One-time import of distinct indicator_code and indicator_name from public.hmis_hmisfact into hmis_indicator_metadata"

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-hiva",
            action="store_true",
            help="Import only indicators where hiva_hfs = true",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without saving anything",
        )

    def handle(self, *args, **options):
        only_hiva = options["only_hiva"]
        dry_run = options["dry_run"]

        where_clause = """
            WHERE indicator_code IS NOT NULL
              AND indicator_name IS NOT NULL
              AND TRIM(indicator_code) <> ''
              AND TRIM(indicator_name) <> ''
        """

        if only_hiva:
            where_clause += " AND hiva_hfs = TRUE "

        sql = f"""
            SELECT DISTINCT
                TRIM(indicator_code) AS indicator_code,
                TRIM(indicator_name) AS indicator_name
            FROM public.hmis_hmisfact
            {where_clause}
            ORDER BY indicator_name, indicator_code
        """

        self.stdout.write(self.style.NOTICE("Reading distinct indicators from public.hmis_hmisfact ..."))

        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        total_found = len(rows)
        created_count = 0
        skipped_count = 0
        error_count = 0

        if total_found == 0:
            self.stdout.write(self.style.WARNING("No indicators found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {total_found} distinct indicators."))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run mode enabled. No records will be saved."))
            for indicator_code, indicator_name in rows[:20]:
                self.stdout.write(f"- {indicator_code} | {indicator_name}")
            if total_found > 20:
                self.stdout.write(f"... and {total_found - 20} more")
            return

        try:
            with transaction.atomic():
                for indicator_code, indicator_name in rows:
                    try:
                        obj, created = IndicatorMetadata.objects.get_or_create(
                            indicator_code=indicator_code,
                            indicator_name=indicator_name,
                            defaults={
                                "indicator_short_name": indicator_name,
                                "data_source": "HMIS",
                                "is_active": True,
                            },
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"CREATED: {indicator_code} | {indicator_name}"
                                )
                            )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"SKIPPED: {indicator_code} | {indicator_name}"
                                )
                            )

                    except Exception as row_error:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"ERROR: {indicator_code} | {indicator_name} | {row_error}"
                            )
                        )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Import failed: {e}"))
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import completed."))
        self.stdout.write(self.style.SUCCESS(f"Created: {created_count}"))
        self.stdout.write(self.style.WARNING(f"Skipped existing: {skipped_count}"))
        self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))