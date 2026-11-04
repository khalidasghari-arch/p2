from django.db import migrations, models
from django.db.models import Q

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name='ReviewMerge', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('source_id', models.PositiveBigIntegerField(db_index=True)),
            ('target_id', models.PositiveBigIntegerField(db_index=True)),
            ('facility_id', models.PositiveBigIntegerField(db_index=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('actor_id', models.PositiveBigIntegerField()),
            ('actor_name', models.CharField(max_length=150)),
            ('verification', models.TextField()),
            ('before', models.JSONField()),
            ('after_digest', models.CharField(max_length=64)),
            ('choices', models.JSONField(default=dict)),
            ('active', models.BooleanField(default=True)),
            ('undone_at', models.DateTimeField(blank=True, null=True)),
            ('undone_by', models.PositiveBigIntegerField(blank=True, null=True)),
        ], options={'ordering':['-pk'], 'permissions':[('merge_mentees','Can transfer and archive duplicate mentees'),('undo_merge','Can undo a mentee merge')],
                    'constraints':[models.UniqueConstraint(fields=['source_id'], condition=Q(active=True), name='one_active_mentee_archive')]}),
        migrations.CreateModel(name='ReviewDecision', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('left_id', models.PositiveBigIntegerField()), ('right_id', models.PositiveBigIntegerField()),
            ('facility_id', models.PositiveBigIntegerField(db_index=True)),
            ('decision', models.CharField(max_length=16, choices=[('different','Different people'),('unsure','Needs verification')])),
            ('note', models.TextField(blank=True)), ('actor_id', models.PositiveBigIntegerField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
    ]
