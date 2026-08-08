"""Turn an optional server-side return path into a same-origin internal target."""

from dataclasses import dataclass, field
from string import ascii_letters, digits

# RFC 3986 unreserved characters, the only ones a segment may consist of. Every
# other exclusion this boundary promises follows from this one positive set.
_UNRESERVED = frozenset(ascii_letters + digits + "-._~")

_MAX_LENGTH = 2048
_DEFAULT_PATH = "/"


def _is_valid_internal_path(value: object) -> bool:
    """Decide the whole grammar once, for both the constructor and the resolver.

    A valid target is a raw ASCII path reference inside the same origin: either
    exactly ``/`` or a leading slash followed by unreserved segments. Because
    the rule is a positive character set rather than a list of forbidden ones,
    a scheme, an authority or network-path reference, userinfo, a query, a
    fragment, a backslash, a percent sign and therefore any percent-encoding,
    whitespace, control characters, and non-ASCII characters are all impossible
    without being excluded one by one. Nothing is decoded or rewritten.
    """

    # Exact type, not isinstance: a str subclass may redefine equality, so a
    # value that validates here could still compare differently later.
    if type(value) is not str:
        return False
    if not value or len(value) > _MAX_LENGTH:
        return False
    if value == _DEFAULT_PATH:
        return True
    if not value.startswith("/") or value.endswith("/"):
        return False
    # An empty segment also rules out "//host" and "///host"; "." and ".." are
    # rejected as segments while a dot inside a segment stays legal.
    return all(
        segment and segment not in (".", "..") and _UNRESERVED.issuperset(segment)
        for segment in value[1:].split("/")
    )


@dataclass(frozen=True, slots=True)
class ValidatedInternalDestination:
    """The only form a later callback route may accept as an internal target.

    The path is carried verbatim and is ``repr``-free, so a navigation target
    never reaches a log through an object representation. The object holds no
    origin and no absolute URL, and it cannot be constructed around an invalid
    value: a raw return path can therefore not reach ``Location`` by being
    wrapped in this type.

    Syntactic validity is **not** existence, authorization, or business
    admissibility. The target application still performs its own checks.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not _is_valid_internal_path(self.value):
            # Neutral on purpose: the rejected value never appears in the text.
            raise ValueError("invalid internal destination")


def resolve_internal_destination(
    return_path: str | None,
) -> ValidatedInternalDestination | None:
    """Resolve a missing or valid return path, or reject neutrally.

    A missing return path yields the fixed safe default. A set but invalid one
    yields ``None`` and never falls back to that default: the two situations
    are different, and merging them would silently redirect a manipulated value
    to a working page. Which target and status a rejection produces is a later
    transport decision.
    """

    if return_path is None:
        return ValidatedInternalDestination(_DEFAULT_PATH)
    if not _is_valid_internal_path(return_path):
        return None
    return ValidatedInternalDestination(return_path)
