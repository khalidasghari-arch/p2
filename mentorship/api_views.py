from datetime import date, datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection

class MentorshipVisitFullAPI(APIView):

    def get(self, request):

        province = request.GET.get("province")
        district = request.GET.get("district")
        facility = request.GET.get("facility")

        sql = """
            SELECT *
            FROM vw_mentorship_visit_full
            WHERE 1=1
        """

        params = []

        if province:
            sql += " AND province = %s"
            params.append(province)

        if district:
            sql += " AND district = %s"
            params.append(district)

        if facility:
            sql += " AND hf_name = %s"
            params.append(facility)

        with connection.cursor() as cursor:
            cursor.execute(sql, params)

            columns = [col[0] for col in cursor.description]

            data = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

        # ---------------------------------------------------------
        # Business rule for dashboard:
        # One mentorship visit = unique Visit Date + Mentor
        # Same Visit Date + same Mentor = counted once only
        # ---------------------------------------------------------

        def get_first_existing_value(row, possible_keys):
            """
            Safely get value from row using possible column names.
            This helps if the database view column names differ slightly.
            """
            for key in possible_keys:
                if key in row:
                    return row.get(key)
            return None

        def normalize_visit_date(value):
            """
            Return clean YYYY-MM-DD date string.
            Works for date, datetime, or string values.
            """
            if not value:
                return ""

            if isinstance(value, datetime):
                return value.date().isoformat()

            if isinstance(value, date):
                return value.isoformat()

            # If string like "2026-02-08 07:00:00", keep only date part
            return str(value)[:10]

        def get_month_name(value):
            """
            Return month name from date/datetime/string.
            """
            if not value:
                return ""

            if isinstance(value, datetime):
                return value.strftime("%B")

            if isinstance(value, date):
                return value.strftime("%B")

            try:
                clean_date = str(value)[:10]
                return datetime.strptime(clean_date, "%Y-%m-%d").strftime("%B")
            except Exception:
                return ""

        seen_visit_date_mentor = set()

        for row in data:
            visit_date_value = get_first_existing_value(
                row,
                [
                    "visit_date",
                    "visitdate",
                    "Visit Date",
                    "mentorshipvistfk__visitdate",
                ],
            )

            mentor_value = get_first_existing_value(
                row,
                [
                    "mentor",
                    "mentor_name",
                    "Mentor",
                    "mentor__name",
                ],
            )

            clean_visit_date = normalize_visit_date(visit_date_value)
            clean_mentor = str(mentor_value or "").strip()
            clean_mentor_key = clean_mentor.lower()

            unique_key = f"{clean_visit_date}|{clean_mentor_key}"

            if clean_visit_date and clean_mentor_key:
                if unique_key not in seen_visit_date_mentor:
                    row["visit_by_mentors"] = 1
                    seen_visit_date_mentor.add(unique_key)
                else:
                    row["visit_by_mentors"] = 0
            else:
                row["visit_by_mentors"] = 0

            # Extra useful fields for React dashboard
            row["month"] = get_month_name(visit_date_value)
            row["unique_visit_mentor_key"] = unique_key

        return Response(data)