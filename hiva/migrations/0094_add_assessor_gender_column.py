from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("hiva", "0089_alter_hqipassessmentheader_assessmentteam"),  # change to your latest applied migration
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE hiva_assessor
                ADD COLUMN IF NOT EXISTS gender boolean NULL;
            """,
            reverse_sql="""
                ALTER TABLE hiva_assessor
                DROP COLUMN IF EXISTS gender;
            """,
        ),
    ]
