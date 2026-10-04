import pandas as pd
import pytest


def make_rows(rows):
    """Build an input DataFrame from dicts; missing columns are left out."""
    return pd.DataFrame(rows)


@pytest.fixture
def basic_df():
    # Times in UTC ISO format with Z.
    return pd.DataFrame(
        [
            # before report creation
            dict(exam_id="1", ai_solution="S1", modality="XR", site="A",
                 study_end_ts="2025-01-10T08:00:00Z", ai_result_available_ts="2025-01-10T08:02:00Z",
                 report_created_ts="2025-01-10T08:10:00Z", report_finalized_ts="2025-01-10T08:15:00Z"),
            # during dictation
            dict(exam_id="2", ai_solution="S1", modality="XR", site="A",
                 study_end_ts="2025-01-10T09:00:00Z", ai_result_available_ts="2025-01-10T09:12:00Z",
                 report_created_ts="2025-01-10T09:10:00Z", report_finalized_ts="2025-01-10T09:15:00Z"),
            # too late
            dict(exam_id="3", ai_solution="S2", modality="CT", site="B",
                 study_end_ts="2025-01-10T10:00:00Z", ai_result_available_ts="2025-01-10T10:20:00Z",
                 report_created_ts="2025-01-10T10:05:00Z", report_finalized_ts="2025-01-10T10:10:00Z"),
            # before creation
            dict(exam_id="4", ai_solution="S2", modality="CT", site="B",
                 study_end_ts="2025-04-10T10:00:00Z", ai_result_available_ts="2025-04-10T10:03:00Z",
                 report_created_ts="2025-04-10T10:30:00Z", report_finalized_ts="2025-04-10T10:40:00Z"),
        ]
    )
