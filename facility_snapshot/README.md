# Facility Performance Snapshot add-on

This is an additive, read-only Django app scaffold based on the supplied model files. It creates one facility page that brings together HQIP, QIC/PIP monitoring, MPDSR, AIM-PEE, AIM-PPH, the WHO childbirth checklist, Safe Surgery, mentorship, MNH Skill Lab, G-ANC/G-PNC, and HMIS records.

## Install

1. Copy the `facility_snapshot` directory into the Django project beside the existing apps.
2. Add `facility_snapshot.apps.FacilitySnapshotConfig` to `INSTALLED_APPS`.
3. Add this route to the project's root `urls.py`:

   ```python
   from django.urls import include, path

   urlpatterns += [
       path("facility-snapshot/", include("facility_snapshot.urls")),
   ]
   ```

4. Open `/facility-snapshot/` to select a facility, or open `/facility-snapshot/<facility-id>/` directly.

No migrations are required by this snapshot app.

## Important data checks

- HMIS has no foreign key to `hiva.Facility`. This scaffold uses the candidate match `HMISFact/MonthlySummary.hfid == Facility.hfcode`, requires a unique Facility HF code, and filters to `hiva_hfs=True`; it displays a validation notice. Confirm that the import pipeline writes the same code system before relying on HMIS results.
- The existing models do not include individual RCA cause records or criterion-linked PIP action records. The page therefore shows failed criteria and the available QIC/PIP status fields without inventing causes or actions.
- Mentees have their own facility assignment in addition to the facility recorded on mentorship visits and Skill Lab sessions. The page attributes activity to the event facility and displays this caveat.
- The HQIP history displays counts of Yes/No/N/A criteria. It does not calculate a weighted official HQIP score.

## Access control

Superusers can see all facilities. Other authenticated users can see facilities in their assigned province through `user.profile.province` or `user.userprofile.province`. Adjust `_user_province_id()` if the project's active profile relation differs.

## Next data-model improvement

Add structured RCA and PIP action records linked to `HQIPAssessmentHeader` and, where appropriate, `Criteria`. Useful PIP fields include action, responsible person, due date, status, completion date, and evidence/reference. This app intentionally does not create or migrate those models.
