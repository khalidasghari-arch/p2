import re
from decimal import Decimal, InvalidOperation
import pandas as pd
from django.db import transaction
from django.utils.text import slugify
from hmis.models import HMISFact
from hmis.models import HMISMonthlySummary

NEW_COLUMN_NAMES = [
    # Location + period
    "PROV",          # orgunitlevel3
    "DIST",          # orgunitlevel4
    "HF",            # organisationunitname
    "PERIOD",        # periodid

    # ===== Indicators (35) =====
    "ANC1",
    "ANC2",
    "ANC3",
    "ANC4",
    "ANC-Other",
    "PNC1",
    "PNC2",
    "PNC-Other",
    "OPD-NewPatients-Clients",
    "Uterotonic-third-stage-labor",
    "APH",
    "PPH",
    "Eclampsia",
    "Pre-eclampsia",
    "N-delivery",
    "A-delivery",
    "C-Section",
    "Babies-breastfed-1st-hour",
    "Newborn-resuscitated",
    "LBW",
    "NewbornAlive",
    "NeonatalDeathdue",
    "Stillbirth",
    "StillbirthFresh",
    "StillbirthRotten",
    "Sepsis",
    "Asphyxia",
    "Other-Neonatal-Complication",
    "Premature",
    "Neonatal-D-due-preterm-Birth",
    "Neonatal-D-due-Sepsis",
    "Neonatal-D-due-Other-causes",
    "Neonatal-D-due-Asphyxia",
    "Maternal-deaths-at-the-clinics",
    "Total-number-of-Neonatal-deaths",

    # ===== Derived columns (6) =====
    "HFName_cleaned",
    "ID",
    "HIVA-HFs",
    "year",
    "month",
    "month_name",
]

LOOKUP_HIVA = [
    91,202,213,216,223,270,1100,95,1511,1078,99,267,2453,2113,231,238,226,2114,809,810,805,
    495,1163,1212,315,2676,320,325,10426,341,346,3773,330,1880,1896,1537.857,2244,855,856,
    1057,1732,1859,403,417,1167,407,424,425,406,1537,857,1537,10420,261
]

DROP_COLS = [
    "orgunitlevel1", "orgunitlevel2", "orgunitlevel5",
    "organisationunitid", "organisationunitcode", "organisationunitdescription",
    "periodname", "periodcode", "perioddescription",
]

def parse_csv_to_df(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df

def apply_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    adb = df.copy()

    # Step 1
    adb["HFName_cleaned"] = adb["organisationunitname"].astype(str).str.replace(
        r"\(\s*(\d+)\s*\)", r"(\1)", regex=True
    )
    adb["HFName_cleaned"] = adb["HFName_cleaned"].str.replace(
        r"\(\s*Info\s*\)", r"(Info)", regex=True
    )

    # Step 2
    adb["ID"] = adb["HFName_cleaned"].str.extract(
        r"\((\d+)\)(?!.*\(\d+\))"
    ).fillna(0).astype(int)

    # Step 3
    adb["HIVA-HFs"] = adb["ID"].isin(LOOKUP_HIVA)

    # Step 4
    adb["periodid"] = adb["periodid"].astype(str)
    adb["year"] = adb["periodid"].str[:4].astype(int)
    adb["month"] = adb["periodid"].str[4:6].astype(int)
    adb["month_name"] = pd.to_datetime(adb["periodid"], format="%Y%m").dt.strftime("%B")

    # Step 5
    adb = adb.drop([c for c in DROP_COLS if c in adb.columns], axis=1)

    # Step 6/7
    if adb.shape[1] != len(NEW_COLUMN_NAMES):
        raise ValueError(
            f"DHIS export structure changed. After dropping columns, got {adb.shape[1]} columns "
            f"but NEW_COLUMN_NAMES expects {len(NEW_COLUMN_NAMES)}.\n"
            f"Fix: Update NEW_COLUMN_NAMES to match your export."
        )

    adb.columns = NEW_COLUMN_NAMES
    return adb

def to_long(cleaned: pd.DataFrame) -> pd.DataFrame:
    # indicator columns are ANC1 ... Total-number-of-Neonatal-deaths
    start = cleaned.columns.get_loc("ANC1")
    end = cleaned.columns.get_loc("Total-number-of-Neonatal-deaths")
    indicator_cols = cleaned.columns[start:end + 1].tolist()

    long_df = cleaned.melt(
        id_vars=["PROV", "DIST", "HF", "PERIOD", "HFName_cleaned", "ID", "HIVA-HFs", "year", "month", "month_name"],
        value_vars=indicator_cols,
        var_name="indicator_name",
        value_name="value_raw",
    )

    long_df["value_raw"] = pd.to_numeric(long_df["value_raw"], errors="coerce")
    long_df = long_df[long_df["value_raw"].notna()].copy()

    long_df["indicator_code"] = long_df["indicator_name"].astype(str).apply(lambda x: slugify(x)[:128])
    return long_df

def _to_decimal(x):
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError):
        return None

@transaction.atomic
def load_replace(upload, long_df: pd.DataFrame, chunk_size: int = 5000) -> dict:
    periods = long_df["PERIOD"].astype(str).str.strip().unique().tolist()
    hfs = long_df["HF"].astype(str).unique().tolist()

    deleted = HMISFact.objects.filter(hf__in=hfs, periodcode__in=periods).delete()[0]

    objs = []
    inserted = 0

    for _, r in long_df.iterrows():
        val = _to_decimal(r["value_raw"])
        if val is None:
            continue

        objs.append(HMISFact(
            source_upload=upload,
            prov=str(r["PROV"] or ""),
            dist=str(r["DIST"] or ""),
            hf=str(r["HF"] or ""),

            periodcode=str(r["PERIOD"]),
            year=int(r["year"]),
            month=int(r["month"]),
            month_name=str(r["month_name"] or ""),

            hf_name_cleaned=str(r["HFName_cleaned"] or ""),
            hfid=int(r["ID"]),
            hiva_hfs=bool(r["HIVA-HFs"]),

            indicator_name=str(r["indicator_name"]),
            indicator_code=str(r["indicator_code"]),
            value=val,
        ))

        if len(objs) >= chunk_size:
            HMISFact.objects.bulk_create(objs, batch_size=chunk_size)
            inserted += len(objs)
            objs = []

    if objs:
        HMISFact.objects.bulk_create(objs, batch_size=chunk_size)
        inserted += len(objs)

    return {"deleted": int(deleted), "inserted": int(inserted)}


def run_import(upload) -> dict:
    df = parse_csv_to_df(upload.file.path)
    cleaned = apply_cleaning(df)
    load_summary_replace(upload, cleaned)
    long_df = to_long(cleaned)
    load_report = load_replace(upload, long_df)

    report = {
        "raw_rows": int(len(df)),
        "cleaned_rows": int(len(cleaned)),
        "long_rows": int(len(long_df)),
        "load": load_report,
    }

    upload.row_count = int(len(df))
    upload.hf_count = int(cleaned["HF"].nunique(dropna=True))
    upload.period_min = str(cleaned["PERIOD"].min())
    upload.period_max = str(cleaned["PERIOD"].max())
    upload.report = report
    upload.status = "IMPORTED"
    upload.save(update_fields=["row_count", "hf_count", "period_min", "period_max", "report", "status"])
    return report

@transaction.atomic
def load_summary_replace(upload, cleaned, chunk_size=2000):
    # Replace by HF + PERIOD (simple and reliable)
    periods = cleaned["PERIOD"].astype(str).unique().tolist()
    hfs = cleaned["HF"].astype(str).unique().tolist()
    HMISMonthlySummary.objects.filter(hf__in=hfs, periodcode__in=periods).delete()

    # Map cleaned column names -> summary fields
    def dec(x):
        try:
            if pd.isna(x): return None
            return Decimal(str(x))
        except Exception:
            return None

    objs = []
    for _, r in cleaned.iterrows():
        objs.append(HMISMonthlySummary(
            source_upload=upload,
            prov=str(r.get("PROV","") or ""),
            dist=str(r.get("DIST","") or ""),
            hf=str(r.get("HF","") or ""),
            periodcode=str(r.get("PERIOD","") or ""),
            year=int(r.get("year") or 0),
            month=int(r.get("month") or 0),
            month_name=str(r.get("month_name","") or ""),
            hfid=int(r.get("ID") or 0),
            hiva_hfs=bool(r.get("HIVA-HFs")),

            anc1=dec(r.get("ANC1")),
            anc2=dec(r.get("ANC2")),
            anc3=dec(r.get("ANC3")),
            anc4=dec(r.get("ANC4")),
            pnc1=dec(r.get("PNC1")),
            pnc2=dec(r.get("PNC2")),
            n_delivery=dec(r.get("N-delivery")),
            a_delivery=dec(r.get("A-delivery")),
            c_section=dec(r.get("C-Section")),
            lbw=dec(r.get("LBW")),
            stillbirth=dec(r.get("Stillbirth")),
        ))

        if len(objs) >= chunk_size:
            HMISMonthlySummary.objects.bulk_create(objs, batch_size=chunk_size)
            objs = []

    if objs:
        HMISMonthlySummary.objects.bulk_create(objs, batch_size=chunk_size)

