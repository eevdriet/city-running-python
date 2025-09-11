import datetime
from typing import override

import gpxpy

from crunner.common import RUNS_PATH
from crunner.excel.header import Header
from crunner.excel.updaters import ExcelUpdater
from crunner.gpx import find_distance


class RunUpdater(ExcelUpdater):
    def __init__(self, area: str, should_overwrite: list[bool] = [True, True, True]):
        headers = [Header.DISTANCE_ACTUAL, Header.COMPLETED, Header.DATE_COMPLETED]

        super().__init__("Runs", area, headers, should_overwrite=should_overwrite)

    @override
    def _find_new_values(self) -> tuple[float | None, bool, datetime.datetime | None]:
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                gpx = gpxpy.parse(file)

            distance = find_distance(gpx, "km")
            is_completed = True
            date_completed = gpx.time
            date_completed = (
                date_completed.replace(tzinfo=None) if date_completed else None
            )

            return distance, is_completed, date_completed
        except:
            print(f"Could not find DT for {self.path}, returning None...")
            return None, True, None

    @override
    def find_paths(self):
        path = RUNS_PATH / self.area
        print(f"Finding paths from: {path.resolve()}")

        return path.rglob("*.gpx")
