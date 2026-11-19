# Facility Performance Snapshot add-on

This is an additive, read-only Django app scaffold based on the supplied model files. It creates one facility page that brings together HQIP, QIC/PIP monitoring, MPDSR, AIM-PEE, AIM-PPH, the WHO childbirth checklist, Safe Surgery, mentorship, MNH Skill Lab, G-ANC/G-PNC, and HMIS records. Matching facility-level records are not capped to a recent-row sample; HQIP assessment rounds are loaded dynamically with no three-round limit. Each record has an expandable list of its saved fields, including related-record names and IDs. G-ANC/G-PNC patient-level clinical values are summarized by field instead of exposing individual rows.

The snapshot uses a responsive full-width layout. On desktop, section navigation stays on the right; on smaller screens it moves above the content. Every table column has a clickable A–Z/Z–A sort control, including the complete-record column. Link underlines and green link text are removed for a cleaner interface.

HQIP summary tables follow `HQIPAssessmentDashboardAdmin`: Standard % = Yes ÷ (Yes + No) × 100; Section % = mean of its scored Standard percentages; Thematic Area % = mean of its scored Section percentages; Overall HQIP % = mean of scored Thematic Area percentages. The code uses score IDs 1, 2, and 3 for Yes, No, and N/A. N/A, missing, and unrecognized responses are excluded from the Standard denominator. Each round is calculated separately; Grand Total across rounds is the mean of available round results for the corresponding row.

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
- G-ANC/G-PNC shows facility-level cohort and activity counts plus a field-coverage summary across the clinical session and delivery models; individual maternal/newborn clinical records and patient identifiers remain in their existing source module.

## Access control

Superusers can see all facilities. Other authenticated users can see facilities in their assigned province through `user.profile.province` or `user.userprofile.province`. Adjust `_user_province_id()` if the project's active profile relation differs.

## Next data-model improvement

Add structured RCA and PIP action records linked to `HQIPAssessmentHeader` and, where appropriate, `Criteria`. Useful PIP fields include action, responsible person, due date, status, completion date, and evidence/reference. This app intentionally does not create or migrate those models.
