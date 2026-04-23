from django.db import migrations


def copy_staff_to_skilllab_mentee(apps, schema_editor):
    Staff = apps.get_model("mentorship", "Staff")
    SkillLabMentee = apps.get_model("skill_lab", "Skill_Lab_Mentee")

    for staff in Staff.objects.all():
        mentee = None

        # 1. Try match by tazkira (strongest unique)
        if staff.tazkiranumber:
            mentee = SkillLabMentee.objects.filter(
                tazkiranumber=staff.tazkiranumber
            ).first()

        # 2. Fallback match
        if mentee is None:
            mentee = SkillLabMentee.objects.filter(
                firstname=staff.firstname,
                lastname=staff.lastname,
                fathername=staff.fathername,
                hfname_id=staff.hfname_id,
                position_id=staff.position_id,
            ).first()

        # 3. Update existing
        if mentee:
            changed = False

            if not mentee.hfname_id and staff.hfname_id:
                mentee.hfname_id = staff.hfname_id
                changed = True

            if not mentee.firstname and staff.firstname:
                mentee.firstname = staff.firstname
                changed = True

            if not mentee.lastname and staff.lastname:
                mentee.lastname = staff.lastname
                changed = True

            if not mentee.fathername and staff.fathername:
                mentee.fathername = staff.fathername
                changed = True

            if not mentee.position_id and staff.position_id:
                mentee.position_id = staff.position_id
                changed = True

            if not mentee.tazkiranumber and staff.tazkiranumber:
                mentee.tazkiranumber = staff.tazkiranumber
                changed = True

            if mentee.gender is None and staff.gender is not None:
                mentee.gender = staff.gender
                changed = True

            if mentee.status is None and staff.status is not None:
                mentee.status = staff.status
                changed = True

            if changed:
                mentee.save()

        # 4. Create new
        else:
            SkillLabMentee.objects.create(
                hfname_id=staff.hfname_id,
                firstname=staff.firstname,
                lastname=staff.lastname,
                fathername=staff.fathername,
                position_id=staff.position_id,
                tazkiranumber=staff.tazkiranumber,
                gender=staff.gender,
                status=staff.status,
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("skill_lab", "0005_alter_skilllab_options_and_more"),  # 👈 IMPORTANT
        ("mentorship", "0001_initial"),  # adjust if needed
    ]

    operations = [
        migrations.RunPython(copy_staff_to_skilllab_mentee, noop_reverse),
    ]