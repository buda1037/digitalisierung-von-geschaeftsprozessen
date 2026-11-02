from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Zustand(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ZUSTAND_UNBEKANNT: _ClassVar[Zustand]
    NEUWERTIG: _ClassVar[Zustand]
    BESCHAEDIGT: _ClassVar[Zustand]
    GETRAGEN: _ClassVar[Zustand]
ZUSTAND_UNBEKANNT: Zustand
NEUWERTIG: Zustand
BESCHAEDIGT: Zustand
GETRAGEN: Zustand

class Wareneingang(_message.Message):
    __slots__ = ("wareneingang_id", "retouren_id", "zustand", "notiz", "erfasst_am")
    WARENEINGANG_ID_FIELD_NUMBER: _ClassVar[int]
    RETOUREN_ID_FIELD_NUMBER: _ClassVar[int]
    ZUSTAND_FIELD_NUMBER: _ClassVar[int]
    NOTIZ_FIELD_NUMBER: _ClassVar[int]
    ERFASST_AM_FIELD_NUMBER: _ClassVar[int]
    wareneingang_id: str
    retouren_id: str
    zustand: Zustand
    notiz: str
    erfasst_am: str
    def __init__(self, wareneingang_id: _Optional[str] = ..., retouren_id: _Optional[str] = ..., zustand: _Optional[_Union[Zustand, str]] = ..., notiz: _Optional[str] = ..., erfasst_am: _Optional[str] = ...) -> None: ...

class ErfasseWareneingangRequest(_message.Message):
    __slots__ = ("retouren_id", "zustand", "notiz")
    RETOUREN_ID_FIELD_NUMBER: _ClassVar[int]
    ZUSTAND_FIELD_NUMBER: _ClassVar[int]
    NOTIZ_FIELD_NUMBER: _ClassVar[int]
    retouren_id: str
    zustand: Zustand
    notiz: str
    def __init__(self, retouren_id: _Optional[str] = ..., zustand: _Optional[_Union[Zustand, str]] = ..., notiz: _Optional[str] = ...) -> None: ...

class GetWareneingangRequest(_message.Message):
    __slots__ = ("retouren_id",)
    RETOUREN_ID_FIELD_NUMBER: _ClassVar[int]
    retouren_id: str
    def __init__(self, retouren_id: _Optional[str] = ...) -> None: ...

class ListeWareneingaengeRequest(_message.Message):
    __slots__ = ("zustand_filter",)
    ZUSTAND_FILTER_FIELD_NUMBER: _ClassVar[int]
    zustand_filter: Zustand
    def __init__(self, zustand_filter: _Optional[_Union[Zustand, str]] = ...) -> None: ...

class KorrigiereZustandRequest(_message.Message):
    __slots__ = ("wareneingang_id", "neuer_zustand")
    WARENEINGANG_ID_FIELD_NUMBER: _ClassVar[int]
    NEUER_ZUSTAND_FIELD_NUMBER: _ClassVar[int]
    wareneingang_id: str
    neuer_zustand: Zustand
    def __init__(self, wareneingang_id: _Optional[str] = ..., neuer_zustand: _Optional[_Union[Zustand, str]] = ...) -> None: ...
