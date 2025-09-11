import datetime
import json
from typing import override

import gpxpy

from crunner.excel.header import Header
from crunner.excel.updaters import ExcelUpdater
from crunner.gpx import find_distance
from crunner.path import Paths
from crunner.strides import Activity


class StreetsUpdater(ExcelUpdater):
    ACTIVITIES = []
    ACTIVITIES_LOADED = False

    @classmethod
    def __load_activities(cls):
        if cls.ACTIVITIES_LOADED:
            return

        with open(Paths.runs() / "city-strides.json", "r") as file:
            activities = json.load(file)
            cls.ACTIVITIES = [Activity.from_json(a) for a in activities]

        cls.ACTIVITIES_LOADED = True

    def __init__(self, area: str, should_overwrite: list[bool] = [False]):
        headers = [Header.STREETS_COMPLETED]

        super().__init__("Streets", area, headers, should_overwrite=should_overwrite)

    @override
    def _find_new_values(self) -> list[int | None]:
        try:
            self.__load_activities()

            with open(self.path, "r", encoding="utf-8") as file:
                gpx = gpxpy.parse(file)

            date_completed = gpx.time
            date_completed = (
                date_completed.replace(tzinfo=None).date() if date_completed else None
            )

            date_activities = [a for a in self.ACTIVITIES if a.date == date_completed]

            # For multiple activities on the day, just get the completed streets directly
            if len(date_activities) > 1:
                if distance := find_distance(gpx):
                    date_activities.sort(key=lambda a: abs(distance - a.distance))

            return [date_activities[0].completed]

        except:
            print(
                f"Could not find streets completed for {self.path}, returning None..."
            )
            return [None]

    @override
    def find_paths(self):
        path = Paths.runs() / self.area
        print(f"Finding paths from: {path.resolve()}")

        return path.rglob("*.gpx")
