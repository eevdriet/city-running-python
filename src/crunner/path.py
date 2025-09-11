from __future__ import with_statement

from collections import defaultdict
from pathlib import Path
from typing import Generator

DATA_TYPES: dict[str, str] = {
    "area": ".json",
    "circuit": ".json",
    "gpx": ".gpx",
    "graph": ".graphml",
    "map": ".html",
    "plotted": ".gpx",
    "polygon": ".csv",
    "runs": ".gpx",
}


class Paths:
    """
    Utility class to quickly navigate the folder structure of the project
    """

    __ROOT = Path(__file__).parent.parent.parent.parent

    @classmethod
    def root(cls) -> Path:
        return cls.__ROOT

    @classmethod
    def data(cls):
        return cls.root() / "data"

    @classmethod
    def relative(cls, path: Path):
        return path.relative_to(cls.data())

    @classmethod
    def data_type(cls, path: Path):
        return cls.relative(path).parts[0]

    @classmethod
    def region(cls, path: Path):
        return cls.relative(path).parts[1]

    @classmethod
    def dir(cls, path: Path):
        return cls.relative(path).parts[-2]

    @classmethod
    def find(
        cls, suffix: Path, allow_cross_over: bool = False
    ) -> Generator[Path, None, None]:
        typ_areas = defaultdict(set)

        for path in cls.data().rglob("*"):
            # print(path)
            if not path.is_file():
                continue

            base = cls.relative(path)
            typ, area = base.parts[:2]

            if typ in ["excel", "osm", "html", "streets"] or area.startswith("Temp"):
                continue

            if (
                typ in typ_areas
                and len(typ_areas[typ] - {area}) > 0
                and not allow_cross_over
            ):
                print(f"Areas for {typ}: ", typ_areas[typ])
                return

            # Compare directories
            n_parts = len(suffix.parts)
            if path.parts[-n_parts:-1] != suffix.parts[:-1]:
                # print(f"\t{path.parts} v.s. {suffix.parts}")
                continue

            # Compare file without stem
            matches = [
                not suffix.suffix and path.stem == suffix.stem,
                path.name == suffix.name,
            ]

            if any(matches):
                typ_areas[area].add(typ)
                yield path

    @classmethod
    def __safe_path(cls, path: Path) -> Path:
        """
        Get the safe version of a path, i.e. ensure all its parents exist
        :param path: Path to provide safety for
        :return: Same path, with as post-condition that all its parents exist
        """
        parent = path if path.is_dir() else path.parent
        parent.mkdir(parents=True, exist_ok=True)

        return path

    """
    graph/Rotterdam/Essen.graphml      Groningen/Yeet.graphml
    graph/Rotterdam/Essen.graphml      Groningen/Yeet.graphml
    """

    @classmethod
    def resolve(
        cls, base_path: Path, suffix: Path, extension: str | None = None
    ) -> Path:
        parts = list(base_path.parts)
        for idx, part in enumerate(reversed(suffix.parts), start=1):
            parts[-idx] = part

        result = Path(*parts)
        return result if extension is None else result.with_suffix(extension)

    @classmethod
    def with_data_type(cls, path: Path, typ: str) -> Path:
        if typ not in DATA_TYPES:
            print(f"Data type {typ} not found, returning unmodified path")
            return path

        ext = DATA_TYPES[typ]
        data_path = cls.data() / typ
        file_path = cls.relative(path)

        return cls.__safe_path(
            (data_path / Path(*file_path.parts[1:])).with_suffix(ext)
        )

    @classmethod
    def _data_type(cls, typ: str, suffix: Path | None = None):
        base_path = cls.__safe_path(cls.data() / typ)
        if suffix is None:
            return base_path

        return cls.with_data_type(suffix, typ)

    @classmethod
    def area(cls, suffix: Path | None = None):
        return cls._data_type("area", suffix)

    @classmethod
    def graph(cls, suffix: Path | None = None):
        return cls._data_type("graph", suffix)

    @classmethod
    def circuit(cls, suffix: Path | None = None):
        return cls._data_type("circuit", suffix)

    @classmethod
    def map(cls, suffix: Path | None = None):
        return cls._data_type("map", suffix)

    @classmethod
    def plotted(cls, suffix: Path | None = None):
        return cls._data_type("plotted", suffix)

    @classmethod
    def html(cls, suffix: str):
        suffix = Path(suffix)
        return cls._data_type("html", suffix)

    @classmethod
    def polygon(cls, suffix: Path | None = None):
        return cls._data_type("polygon", suffix)

    @classmethod
    def runs(cls, suffix: Path | None = None):
        return cls._data_type("runs", suffix)

    @classmethod
    def gpx(cls, suffix: Path | None = None):
        return cls._data_type("gpx", suffix)

    @classmethod
    def excel(cls, area: str | Path) -> Path:
        area = area if isinstance(area, str) else area.stem

        path = cls.data() / "excel" / f"{area}.xlsx"
        return cls.__safe_path(path)


if __name__ == "__main__":
    path = Paths.data() / "graph" / "Rotterdam" / Path("Distripark Botlek.json")
    print("Area", Paths.map(path))
