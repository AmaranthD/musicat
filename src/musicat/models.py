from dataclasses import asdict, dataclass


@dataclass
class Track:
    id: int
    owner_id: str | None
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
    owner_id: str | None
    filename: str
    reason: str
    imported_at: str
    stored_name: str | None = None

    @classmethod
    def from_row(cls, row) -> "UnrecognizedItem":
        return cls(**{key: row[key] for key in row.keys()})

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("stored_name", None)
        data.pop("owner_id", None)
        return data
