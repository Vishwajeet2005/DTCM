"""
csv_importer.py
===============
CSVImporter class for the DTCM project.

Supports importing environmental sensor readings from CSV files or raw bytes,
with schema validation, cleaning, and high-performance bulk insertion.
"""

import io
import logging
from typing import Any

import pandas as pd
from sqlalchemy import insert as sa_insert

logger = logging.getLogger(__name__)


class CSVImporter:
    """
    Import CO2 sensor data from CSV files into the EnvironmentalData table.

    The importer validates the schema, cleans data types, and performs a
    bulk insert using SQLAlchemy Core for maximum throughput.
    """

    REQUIRED_COLUMNS: list[str] = ["sensor_id", "co2_level", "timestamp"]
    OPTIONAL_COLUMNS: list[str] = ["temperature", "humidity", "pm25", "aqi"]

    # Default values used when optional columns are absent
    DEFAULTS: dict[str, Any] = {
        "temperature": None,
        "humidity":    None,
        "pm25":        None,
        "aqi":         None,
        "data_quality": "imported",
        "data_gap":    False,
    }

    # Acceptable CO2 and timestamp ranges for row-level validation
    CO2_MIN, CO2_MAX = 1.0, 10000.0  # generous bounds; outlier removal handles finer cuts

    # ------------------------------------------------------------------
    # 1. Schema validation
    # ------------------------------------------------------------------
    def validate_schema(self, df: pd.DataFrame) -> tuple[bool, str]:
        """
        Verify that *df* contains all required columns.

        Parameters
        ----------
        df : Raw DataFrame loaded from the CSV.

        Returns
        -------
        (is_valid, error_message) : error_message is empty string when valid.
        """
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            msg = f"CSV is missing required column(s): {missing}"
            logger.error("validate_schema: %s", msg)
            return False, msg

        if df.empty:
            msg = "CSV file contains no data rows."
            logger.warning("validate_schema: %s", msg)
            return False, msg

        logger.debug("validate_schema: OK - %d rows, columns %s.", len(df), list(df.columns))
        return True, ""

    # ------------------------------------------------------------------
    # 2. Parsing and cleaning
    # ------------------------------------------------------------------
    def parse_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Coerce types, parse timestamps, and drop rows missing required fields.

        Steps
        -----
        1. Parse *timestamp* column to datetime; drop un-parseable rows.
        2. Coerce *sensor_id* to int; drop non-numeric rows.
        3. Coerce *co2_level* to float; drop non-numeric rows.
        4. Coerce optional numeric columns, replacing errors with NaN.
        5. Fill missing optional columns with DEFAULTS.
        6. Drop fully duplicate rows.

        Parameters
        ----------
        df : Raw DataFrame (after validate_schema passes).

        Returns
        -------
        Cleaned DataFrame ready for bulk_insert.
        """
        original_len = len(df)
        df = df.copy()

        # ---- Timestamp ----
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=False)
        bad_ts = df["timestamp"].isna().sum()
        if bad_ts:
            logger.warning("parse_and_clean: dropping %d rows with invalid timestamps.", bad_ts)
        df = df.dropna(subset=["timestamp"])

        # ---- sensor_id ----
        df["sensor_id"] = pd.to_numeric(df["sensor_id"], errors="coerce")
        bad_sid = df["sensor_id"].isna().sum()
        if bad_sid:
            logger.warning("parse_and_clean: dropping %d rows with invalid sensor_id.", bad_sid)
        df = df.dropna(subset=["sensor_id"])
        df["sensor_id"] = df["sensor_id"].astype(int)

        # ---- co2_level ----
        df["co2_level"] = pd.to_numeric(df["co2_level"], errors="coerce")
        bad_co2 = df["co2_level"].isna().sum()
        if bad_co2:
            logger.warning("parse_and_clean: dropping %d rows with invalid co2_level.", bad_co2)
        df = df.dropna(subset=["co2_level"])

        # ---- Optional numeric columns ----
        for col in self.OPTIONAL_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = self.DEFAULTS.get(col)  # type: ignore[assignment]

        # ---- data_quality / data_gap defaults ----
        if "data_quality" not in df.columns:
            df["data_quality"] = self.DEFAULTS["data_quality"]
        if "data_gap" not in df.columns:
            df["data_gap"] = self.DEFAULTS["data_gap"]
        else:
            # Coerce to bool
            df["data_gap"] = df["data_gap"].astype(bool)

        # ---- Drop duplicates ----
        df = df.drop_duplicates(subset=["sensor_id", "timestamp"])

        cleaned_len = len(df)
        logger.info(
            "parse_and_clean: %d rows in ? %d rows out (%d dropped).",
            original_len,
            cleaned_len,
            original_len - cleaned_len,
        )
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # 3. Bulk insert
    # ------------------------------------------------------------------
    def bulk_insert(self, df: pd.DataFrame, session) -> dict:
        """
        Insert *df* rows into EnvironmentalData using SQLAlchemy Core insert.

        Uses chunked inserts (1 000 rows per chunk) to avoid hitting SQLite
        parameter limits and to provide partial-progress logging.

        Parameters
        ----------
        df      : Cleaned DataFrame from parse_and_clean.
        session : Active SQLAlchemy session (Flask-SQLAlchemy or plain SA).

        Returns
        -------
        {'inserted': N, 'errors': M}
        """
        from db.models import EnvironmentalData  # type: ignore

        if df.empty:
            logger.warning("bulk_insert: received empty DataFrame - nothing to insert.")
            return {"inserted": 0, "errors": 0}

        table = EnvironmentalData.__table__

        # Build list of dicts; keep only columns that exist in the DB table
        table_cols = {c.name for c in table.columns if c.name != "id"}
        records = []
        for _, row in df.iterrows():
            record: dict[str, Any] = {}
            for col in table_cols:
                val = row.get(col)
                # Convert NaN/NaT to None for SQLAlchemy
                if pd.isna(val) if not isinstance(val, str) else False:
                    record[col] = None
                else:
                    record[col] = val
            records.append(record)

        CHUNK_SIZE = 1000
        inserted = 0
        errors   = 0

        conn = session.connection()  # raw DBAPI connection for Core insert
        for chunk_start in range(0, len(records), CHUNK_SIZE):
            chunk = records[chunk_start: chunk_start + CHUNK_SIZE]
            try:
                conn.execute(sa_insert(table), chunk)
                inserted += len(chunk)
                logger.debug("bulk_insert: inserted chunk %d rows.", len(chunk))
            except Exception as exc:
                # Row-by-row fallback for chunks that fail (e.g. unique violations)
                logger.warning(
                    "Chunk insert failed (%s) - falling back to row-by-row.", exc
                )
                for rec in chunk:
                    try:
                        conn.execute(sa_insert(table), [rec])
                        inserted += 1
                    except Exception as row_exc:
                        errors += 1
                        logger.debug("Row insert error: %s | record: %s", row_exc, rec)

        session.commit()
        logger.info("bulk_insert complete: inserted=%d, errors=%d.", inserted, errors)
        return {"inserted": inserted, "errors": errors}

    # ------------------------------------------------------------------
    # 4. High-level import helpers
    # ------------------------------------------------------------------
    def import_from_file(self, filepath: str, session) -> dict:
        """
        Load a CSV from *filepath*, validate, clean, and bulk insert.

        Parameters
        ----------
        filepath : Absolute or relative path to the CSV file.
        session  : Active SQLAlchemy session.

        Returns
        -------
        {'inserted': N, 'errors': M} or {'inserted': 0, 'errors': -1, 'message': ...}
        """
        try:
            df = pd.read_csv(filepath, low_memory=False)
        except FileNotFoundError:
            msg = f"File not found: {filepath}"
            logger.error("import_from_file: %s", msg)
            return {"inserted": 0, "errors": -1, "message": msg}
        except Exception as exc:
            msg = f"Failed to read CSV: {exc}"
            logger.error("import_from_file: %s", msg)
            return {"inserted": 0, "errors": -1, "message": msg}

        return self._run_pipeline(df, session)

    def import_from_bytes(self, file_bytes: bytes, session) -> dict:
        """
        Load a CSV from raw *file_bytes* (e.g. from an HTTP file upload), then
        validate, clean, and bulk insert.

        Parameters
        ----------
        file_bytes : Raw bytes content of the CSV file.
        session    : Active SQLAlchemy session.

        Returns
        -------
        {'inserted': N, 'errors': M} or {'inserted': 0, 'errors': -1, 'message': ...}
        """
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), low_memory=False)
        except Exception as exc:
            msg = f"Failed to parse CSV bytes: {exc}"
            logger.error("import_from_bytes: %s", msg)
            return {"inserted": 0, "errors": -1, "message": msg}

        return self._run_pipeline(df, session)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _run_pipeline(self, df: pd.DataFrame, session) -> dict:
        """
        Internal helper: validate ? clean ? bulk insert.

        Parameters
        ----------
        df      : Raw DataFrame.
        session : Active SQLAlchemy session.

        Returns
        -------
        Result dict from bulk_insert, or error dict.
        """
        is_valid, error_msg = self.validate_schema(df)
        if not is_valid:
            return {"inserted": 0, "errors": -1, "message": error_msg}

        cleaned_df = self.parse_and_clean(df)
        if cleaned_df.empty:
            return {"inserted": 0, "errors": 0, "message": "No valid rows after cleaning."}

        return self.bulk_insert(cleaned_df, session)

