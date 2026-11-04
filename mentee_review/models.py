from django.db import models
from django.db.models import Q

class ReviewMerge(models.Model):
    # IDs are deliberately independent of the mentorship migration numbering.
    source_id = models.PositiveBigIntegerField(db_index=True)
    target_id = models.PositiveBigIntegerField(db_index=True)
    facility_id = models.PositiveBigIntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    actor_id = models.PositiveBigIntegerField()
    actor_name = models.CharField(max_length=150)
    verification = models.TextField()
    before = models.JSONField()
    after_digest = models.CharField(max_length=64)
    choices = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    undone_at = models.DateTimeField(null=True, blank=True)
    undone_by = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['source_id'], condition=Q(active=True), name='one_active_mentee_archive')]
        permissions = [('merge_mentees', 'Can transfer and archive duplicate mentees'),
                       ('undo_merge', 'Can undo a mentee merge')]
        ordering = ['-pk']

class ReviewDecision(models.Model):
    left_id = models.PositiveBigIntegerField()
    right_id = models.PositiveBigIntegerField()
    facility_id = models.PositiveBigIntegerField(db_index=True)
    decision = models.CharField(max_length=16, choices=[('different','Different people'), ('unsure','Needs verification')])
    note = models.TextField(blank=True)
    actor_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
