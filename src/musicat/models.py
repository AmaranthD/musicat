from dataclasses import asdict, dataclass


@dataclass
class Track:
    id: int
    content_hash: str
    filename: str
    stored_name: str
    title: str | None
    artist: str | None
    album: str | None
    duration: float | None
    format: str | None
    imported_at: str

    @classmethod
    def from_row(cls, row) -> "Track":
        return cls(**{key: row[key] for key in row.keys()})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UnrecognizedItem:
    id: int
    filename: str
    reason: str
    imported_at: str

    @classmethod
    def from_row(cls, row) -> "UnrecognizedItem":
        return cls(**{key: row[key] for key in row.keys()})

    def to_dict(self) -> dict:
        return asdict(self)
