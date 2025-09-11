from pathlib import Path


def find_path_name(path: Path) -> Path:
    ancestor = path.parent
    while ancestor.name != "data":
        ancestor = ancestor.parent

    return path.relative_to(ancestor)


def ends_with(path: Path, suffix: Path) -> bool:
    # Compare directories directly
    n_parts = len(suffix.parts)
    if path.parts[-n_parts:-1] != suffix.parts[:-1]:
        return False

    # Compare file without stem
    return (
        not suffix.suffixes and path.stem == suffix.stem
    ) or path.suffixes == suffix.suffixes
