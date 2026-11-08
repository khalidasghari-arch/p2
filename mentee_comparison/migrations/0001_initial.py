from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

SKILL_MODEL = getattr(settings, 'MENTEE_COMPARISON_SKILL_MODEL', 'skilllab.Skill_Lab_Mentee')


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mentorship', '__first__'),
        (SKILL_MODEL.split('.')[0], '__first__'),
    ]
    operations = [migrations.CreateModel(
        name='MenteeMatch',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('confirmed_at', models.DateTimeField(auto_now_add=True)),
            ('note', models.CharField(blank=True, max_length=500)),
            ('confirmed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ('staff', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='mentorship.staff')),
            ('skill_mentee', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=SKILL_MODEL)),
        ],
        options={
            'verbose_name': 'Mentee comparison dashboard',
            'verbose_name_plural': 'Mentee comparison dashboard',
            'permissions': [('confirm_matches', 'Can confirm and remove mentee comparison links')],
        },
    )]
