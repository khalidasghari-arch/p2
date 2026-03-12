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

        return Response(data)