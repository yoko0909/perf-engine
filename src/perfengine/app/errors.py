from dataclasses import dataclass


@dataclass(slots=True)
class OperatorError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message
