import os
import sys
from datetime import datetime

import pytest

# Ensure the DateCorrector module can be imported without triggering package imports
MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'ev_charging_extractor'))
if MODULE_PATH not in sys.path:
    sys.path.insert(0, MODULE_PATH)

from date_correction_script import DateCorrector


@pytest.mark.parametrize(
    "provider, raw_data, expected",
    [
        (
            "Tesla",
            "Invoice date 2024/03/01\nOther text",
            datetime(2024, 3, 1),
        ),
        (
            "BP Pulse",
            "Some text\nStart Time: Mar 25, 2024 at 10:23:00 AM\nMore text",
            datetime(2024, 3, 25),
        ),
    ],
)
def test_extract_date_from_raw_data(provider, raw_data, expected):
    corrector = DateCorrector(":memory:")
    result = corrector.extract_date_from_raw_data(raw_data, provider)
    assert result == expected
