from django.db import migrations


def copy_mentorship_master_data(apps, schema_editor):
    ThematicMentorship = apps.get_model("mentorship", "ThematicMentorship")
    MentorshipTopics = apps.get_model("mentorship", "MentorshipTopics")

    ThematicArea = apps.get_model("skill_lab", "ThematicArea")
    SkillLabTopic = apps.get_model("skill_lab", "SkillLabTopic")

    # Map old thematic mentorship IDs to new skill lab thematic IDs
    thematic_id_map = {}

    # -----------------------------------------
    # 1. Copy ThematicMentorship -> ThematicArea
    # -----------------------------------------
    for old_thematic in ThematicMentorship.objects.all():
        new_thematic, created = ThematicArea.objects.get_or_create(
            name=old_thematic.name,
            defaults={
                "shortname": old_thematic.shortname,
                "hqip_area_id": old_thematic.hqip_area_id,
            },
        )

        updated = False

        if not new_thematic.shortname and old_thematic.shortname:
            new_thematic.shortname = old_thematic.shortname
            updated = True

        if not new_thematic.hqip_area_id and old_thematic.hqip_area_id:
            new_thematic.hqip_area_id = old_thematic.hqip_area_id
            updated = True

        if updated:
            new_thematic.save()

        thematic_id_map[old_thematic.id] = new_thematic.id

    # -----------------------------------------
    # 2. Copy MentorshipTopics -> SkillLabTopic
    # -----------------------------------------
    for old_topic in MentorshipTopics.objects.all():
        new_thematic_id = thematic_id_map.get(old_topic.thematicfk_id)

        # avoid duplicates inside same thematic area
        existing = SkillLabTopic.objects.filter(
            thematicfk_id=new_thematic_id,
            name=old_topic.name,
        ).first()

        if existing:
            updated = False

            if not existing.shortname and old_topic.shortname:
                existing.shortname = old_topic.shortname
                updated = True

            if not existing.namedari and old_topic.namedari:
                existing.namedari = old_topic.namedari
                updated = True

            if not existing.namepashto and old_topic.namepashto:
                existing.namepashto = old_topic.namepashto
                updated = True

            if not existing.nameeng and old_topic.nameeng:
                existing.nameeng = old_topic.nameeng
                updated = True

            if not existing.track and old_topic.track:
                existing.track = old_topic.track
                updated = True

            if (existing.seq_no in [None, 0]) and old_topic.seq_no:
                existing.seq_no = old_topic.seq_no
                updated = True

            if updated:
                existing.save()

            continue

        SkillLabTopic.objects.create(
            thematicfk_id=new_thematic_id,
            shortname=old_topic.shortname,
            name=old_topic.name,
            namedari=old_topic.namedari,
            namepashto=old_topic.namepashto,
            nameeng=old_topic.nameeng,
            track=old_topic.track or "",
            seq_no=old_topic.seq_no or 0,
        )


def reverse_noop(apps, schema_editor):
    """
    Intentionally left blank to avoid deleting manually entered skill_lab data.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("skill_lab", "0001_initial"),
        ("mentorship", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_mentorship_master_data, reverse_noop),
    ]