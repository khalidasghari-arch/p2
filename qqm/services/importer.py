import math
import pandas as pd
from django.db import transaction
from openpyxl.utils.cell import column_index_from_string

STRUCTURAL_SHEET = "Annex1b-Structural_FAC"
EXIT_VIGNETTE_SHEET = "Annex 2b-QQC_EXIT&VIGNETTES_FAC"
WORKFORCE_SHEET = "Annex 3b-HEALTHWORKFORCE - FAC"
MSS_SHEET = "Annex 4b-MSS - FAC"

def clean_hfcode(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, float):
        if math.isnan(value):
            return None
        value = int(value)

    value = str(value).strip().replace(".0", "")

    if value.lower() in ["", "nan", "none", "facility id", "facid", "facid1"]:
        return None

    value = value.lstrip("0")

    if not value:
        return None

    try:
        return int(value)
    except Exception:
        return None

def clean_float(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, str):
        value = value.strip().replace("%", "")
        if value == "":
            return None

    try:
        return float(value)
    except Exception:
        return None

def safe_json(row):
    if row is None:
        return {}

    data = {}

    try:
        row_dict = row.to_dict()
    except Exception:
        return {}

    for key, value in row_dict.items():
        key = str(key)

        try:
            if pd.isna(value):
                data[key] = None
            elif hasattr(value, "isoformat"):
                data[key] = value.isoformat()
            else:
                data[key] = value
        except Exception:
            data[key] = str(value)

    return data

def load_sheet(file_path, sheet_name, header_row, keep_columns=False):
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=header_row,
        engine="openpyxl",
    )
    df = df.dropna(how="all")

    # Important:
    # For Structural sheet, do NOT drop empty columns.
    # We need exact Excel column letters: N, AD, BH, BU, CK, CW, DE, DV, EQ, FE.
    if not keep_columns:
        df = df.dropna(axis=1, how="all")

    return df

def get_col(df, possible_names):
    for wanted in possible_names:
        for col in df.columns:
            if str(col).strip().lower() == wanted.lower():
                return col

    for wanted in possible_names:
        for col in df.columns:
            if wanted.lower() in str(col).strip().lower():
                return col

    return None

def build_lookup(df, possible_hfcode_columns):
    hf_col = get_col(df, possible_hfcode_columns)

    if hf_col is None:
        return {}

    lookup = {}

    for _, row in df.iterrows():
        hfcode = clean_hfcode(row.get(hf_col))
        if hfcode:
            lookup[hfcode] = row

    return lookup

def get_facility_by_hfcode(hfcode):
    from hiva.models import Facility

    possible_fields = [
        "hfcode",
        "HFCODE",
        "hfid",
        "HFCode",
        "hfcodes",
    ]

    for field in possible_fields:
        try:
            facility = Facility.objects.filter(**{field: hfcode}).first()
            if facility:
                return facility
        except Exception:
            continue

    return None

def get_hfname_from_rows(*rows):
    possible_names = [
        "Facility Name",
        "Health Facility",
        "HF Name",
        "Facility",
        "Name of Facility",
    ]

    for row in rows:
        if row is None:
            continue

        for col in row.index:
            col_name = str(col).strip()
            if col_name in possible_names:
                value = row.get(col)
                try:
                    if value is not None and not pd.isna(value):
                        return str(value).strip()
                except Exception:
                    if value:
                        return str(value).strip()

    return None

def get_last_numeric_value(row):
    if row is None:
        return None

    values = list(row.values)

    for value in reversed(values):
        number = clean_float(value)
        if number is not None:
            return number

    return None

def get_structural_score(row):
    if row is None:
        return None

    possible_cols = [
        "Overall Structural Score",
        "Structural Score",
        "Overall score",
        "Overall Score",
        "Score",
    ]

    for col in row.index:
        if str(col).strip() in possible_cols:
            value = clean_float(row.get(col))
            if value is not None:
                return value

    return get_last_numeric_value(row)

def get_outcome_score(row):
    if row is None:
        return None

    possible_cols = [
        "Outcome quality",
        "Outcome Quality",
        "Outcome quality score",
        "Outcome Quality Score",
        "Final outcome quality score",
    ]

    for col in row.index:
        if str(col).strip() in possible_cols:
            value = clean_float(row.get(col))
            if value is not None:
                return value

    return get_last_numeric_value(row)

def get_content_score(row):
    if row is None:
        return None

    possible_cols = [
        "Content of Care Quality score",
        "Content of Care Quality Score",
        "Content of care score",
        "Content Score",
        "Content quality score",
    ]

    for col in row.index:
        if str(col).strip() in possible_cols:
            value = clean_float(row.get(col))
            if value is not None:
                return value

    return get_last_numeric_value(row)

def safe_value_by_position(row, position):
    if row is None:
        return None

    try:
        return clean_float(row.iloc[position])
    except Exception:
        return None

def get_value_by_excel_column(row, column_letter):
    if row is None:
        return None

    try:
        index = column_index_from_string(column_letter) - 1
        return clean_float(row.iloc[index])
    except Exception:
        return None

def extract_structural_domains(row):
    """
    Exact structural domain columns from Annex1b-Structural_FAC:

    N  = Domain 1: General Management
    AD = Domain 2: Hygiene
    BH = Domain 3: OPD / Curative Consultations
    BU = Domain 4: Family Planning
    CK = Domain 5: Laboratory
    CW = Domain 6: Essential Drugs Management
    DE = Domain 7: Tracer Drugs
    DV = Domain 8: Maternity
    EQ = Domain 9: EPI
    FE = Domain 10: Antenatal Care
    """

    return {
        "d1_general_management": get_value_by_excel_column(row, "N"),
        "d2_hygiene": get_value_by_excel_column(row, "AD"),
        "d3_opd": get_value_by_excel_column(row, "BH"),
        "d4_fp": get_value_by_excel_column(row, "BU"),
        "d5_lab": get_value_by_excel_column(row, "CK"),
        "d6_drugs": get_value_by_excel_column(row, "CW"),
        "d7_tracer": get_value_by_excel_column(row, "DE"),
        "d8_maternity": get_value_by_excel_column(row, "DV"),
        "d9_epi": get_value_by_excel_column(row, "EQ"),
        "d10_anc": get_value_by_excel_column(row, "FE"),
    }

def calculate_qqm(structural_score, outcome_score, content_score):
    if structural_score is None or outcome_score is None or content_score is None:
        return None

    return round(
        (structural_score * 0.40)
        + (outcome_score * 0.20)
        + (content_score * 0.40),
        4,
    )

@transaction.atomic
def process_qqm_upload(upload_id):
    from qqm.models import (
        QQMUpload,
        QQMFacilityScore,
        QQMRawData,
        QQMStructuralDetail,
    )

    upload = QQMUpload.objects.select_for_update().get(id=upload_id)
    upload.status = "processing"
    upload.processed = False
    upload.error_message = None
    upload.save(update_fields=["status", "processed", "error_message"])

    try:
        file_path = upload.excel_file.path

        structural_df = load_sheet(file_path, STRUCTURAL_SHEET,
        header_row=1,
        keep_columns=True,
        )
        exit_df = load_sheet(file_path, EXIT_VIGNETTE_SHEET, header_row=2)
        workforce_df = load_sheet(file_path, WORKFORCE_SHEET, header_row=2)
        mss_df = load_sheet(file_path, MSS_SHEET, header_row=2)

        structural_lookup = build_lookup(
            structural_df,
            ["Facility ID", "HFCode", "HF Code", "HFID", "Facility code"],
        )

        outcome_lookup = build_lookup(
            exit_df,
            ["Facility ID", "HFCode", "HF Code", "HFID", "Facility code"],
        )

        content_lookup = build_lookup(
            exit_df,
            ["Facility ID.1", "HFCode.1", "HF Code.1", "HFID.1", "Facility code.1"],
        )

        workforce_lookup = build_lookup(
            workforce_df,
            ["Facility ID", "HFCode", "HF Code", "HFID", "Facility code"],
        )

        mss_lookup = build_lookup(
            mss_df,
            ["Facility ID", "HFCode", "HF Code", "HFID", "Facility code"],
        )

        all_hfcodes = set()
        all_hfcodes.update(structural_lookup.keys())
        all_hfcodes.update(outcome_lookup.keys())
        all_hfcodes.update(content_lookup.keys())
        all_hfcodes.update(workforce_lookup.keys())
        all_hfcodes.update(mss_lookup.keys())

        QQMFacilityScore.objects.filter(upload=upload).delete()

        imported = 0
        matched = 0
        unmatched = 0

        for hfcode in sorted(all_hfcodes):
            structural_row = structural_lookup.get(hfcode)
            outcome_row = outcome_lookup.get(hfcode)
            content_row = content_lookup.get(hfcode)
            workforce_row = workforce_lookup.get(hfcode)
            mss_row = mss_lookup.get(hfcode)

            facility = get_facility_by_hfcode(hfcode)

            if facility:
                matched += 1
            else:
                unmatched += 1

            hfname_excel = get_hfname_from_rows(
                structural_row,
                outcome_row,
                content_row,
                workforce_row,
                mss_row,
            )

            structural_score = get_structural_score(structural_row)
            outcome_score = get_outcome_score(outcome_row)
            content_score = get_content_score(content_row)

            qqm_score = calculate_qqm(
                structural_score,
                outcome_score,
                content_score,
            )

            score_obj = QQMFacilityScore.objects.create(
                upload=upload,
                facility=facility,
                hfcode=hfcode,
                hfname_excel=hfname_excel,
                structural_score=structural_score,
                outcome_score=outcome_score,
                content_score=content_score,
                qqm_score=qqm_score,
            )

            QQMRawData.objects.create(
                score=score_obj,
                structural_data=safe_json(structural_row),
                exit_vignette_data={
                    "outcome": safe_json(outcome_row),
                    "content": safe_json(content_row),
                },
                workforce_data=safe_json(workforce_row),
                mss_data=safe_json(mss_row),
            )

            structural_domain_values = extract_structural_domains(structural_row)

            QQMStructuralDetail.objects.create(
                score=score_obj,
                **structural_domain_values,
            )

            imported += 1

        upload.status = "done"
        upload.processed = True
        upload.total_imported = imported
        upload.total_matched_facilities = matched
        upload.total_unmatched_facilities = unmatched
        upload.error_message = None
        upload.save()

        return {
            "imported": imported,
            "matched": matched,
            "unmatched": unmatched,
            "message": "Processed successfully",
        }

    except Exception as e:
        upload.status = "failed"
        upload.processed = False
        upload.error_message = str(e)
        upload.save(update_fields=["status", "processed", "error_message"])
        raise