from enum import StrEnum
from typing import Any


class Header(StrEnum):
    AREA = "Area"
    DISTANCE = "Distance"
    DISTANCE_ACTUAL = "Actual distance"
    COMPLETED = "Completed?"
    TYPE = "Type"
    LOCATION = "Location"
    TRAVEL_TIME = "Travel time"
    DATE_COMPLETED = "Date completed"
    STREETS_COMPLETED = "Streets completed"
    NOTES = "Notes"


HEADER_OFFSET = 6
HEADERS = [header for header in Header]
HEADER_DEFAULTS: dict[Header, Any] = {
    Header.AREA: None,
    Header.DISTANCE: None,
    Header.DISTANCE_ACTUAL: None,
    Header.COMPLETED: False,
    Header.TYPE: "Run",
    Header.LOCATION: None,
    Header.TRAVEL_TIME: None,
    Header.DATE_COMPLETED: None,
    Header.STREETS_COMPLETED: None,
    Header.NOTES: "",
}


def create_empty_row(area: str):
    cells = HEADER_DEFAULTS.copy()
    cells[Header.AREA] = area
    cells[Header.TYPE] = "Walk" if area.startswith("Volkstuin") else "Run"

    return [cells[header] for header in HEADERS]
