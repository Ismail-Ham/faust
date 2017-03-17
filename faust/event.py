from typing import Any, FrozenSet, Iterable, Mapping, Tuple, cast
from .types import K, Message, Request
from .utils.serialization import dumps, loads


class Event:
    req: Request = None
    _fields: Mapping[str, type]
    _fieldset = FrozenSet[str]

    @classmethod
    def from_message(cls,
                     key: K,
                     topic: str,
                     partition: int,
                     message: Message) -> 'Event':
        request = Request(key, topic, partition, message)
        return cls.loads(message.value, req=request)

    @classmethod
    def loads(cls, s: Any, **kwargs) -> 'Event':
        return cls(**kwargs, **loads(cls.serializer, s))

    def __init_subclass__(cls, serializer: str = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.serializer = serializer
        fields = {}
        wanted_baseclass = False
        for cls in reversed(cls.__mro__):
            if wanted_baseclass:
                try:
                    fields.update(cls.__annotations__)
                except AttributeError:
                    pass
            else:
                wanted_baseclass = cls == Event
        cls._fields = cast(Mapping, fields)
        cls._fieldset = frozenset(fields)

    def __init__(self, **fields):
        fieldset = frozenset(fields)
        missing = self._fieldset - fieldset
        if missing:
            raise TypeError('{} missing required arguments: {}'.format(
                type(self).__name__, ', '.join(sorted(missing))))
        extraneous = fieldset - self._fieldset
        if extraneous:
            raise TypeError('{} got unexpected arguments: {}'.format(
                type(self).__name__, ', '.join(sorted(extraneous))))
        self.__dict__.update(fields)

    def dumps(self) -> Any:
        return dumps(self.serializer, self._asdict())

    def _asdict(self) -> Mapping:
        return dict(self._asitems())

    def _asitems(self) -> Iterable[Tuple[Any, Any]]:
        for key in self._fields:
            yield key, self.__dict__[key]

    def __repr__(self) -> str:
        return '<{}: {}>'.format(type(self).__name__, _kvrepr(self.__dict__))


def _kvrepr(d: Mapping[str, Any],
            sep: str = ', ',
            fmt: str = '{0}={1!r}') -> str:
    """Represent dict as `k='v'` pairs separated by comma."""
    return sep.join(
        fmt.format(k, v) for k, v in d.items()
    )


class FieldDescriptor:
    """Describes a field.

    Used in join, etc.::

        A.type.amount & B.type.amount

    where ``.type`` basically creates one descriptor for every
    field in the record.
    """

    field: str

    def __init__(self, field: str) -> None:
        self.field = field

    def join(self, other: 'FieldDescriptor'):  # TODO Returns StreamT
        print('join %r with %r' % (self.field, other.field))
        # TODO Return StreamT

    def __and__(self, other: 'FieldDescriptor') -> Any:
        return self.join(other)

    def __repr__(self) -> str:
        return '<{name}: {self.field}>'.format(
            name=type(self).__name__, self=self)


class BoundEvent:
    """A bound event holds reference to specific stream.

    :class:`FieldDescriptor``'s will be added for every field
    in the event.

    """

    #: The event type object.
    event: type

    #: The object we are bound to.
    obj: Any

    def __init__(self, event: type, obj: Any) -> None:
        self.event = event
        self.obj = obj

        # mypy says 'type' objects don't have __annotations__
        annotations: Mapping = self.event.__annotations__  # type: ignore

        self.__dict__.update({
            field: self._make_field_descriptor(field)
            for field in annotations.keys()
        })

    def _make_field_descriptor(self, field: str) -> FieldDescriptor:
        return FieldDescriptor(field)
