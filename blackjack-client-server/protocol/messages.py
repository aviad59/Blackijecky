# protocol/messages.py
import struct
from dataclasses import dataclass

from protocol.constants import (
    MAGIC_COOKIE,
    MSG_OFFER, MSG_REQUEST, MSG_PAYLOAD,
    NAME_LEN, DECISION_LEN, CARD_LEN
)

# Network byte order (!)
OFFER_FMT = "!IBH32s"        # cookie(4) type(1 as B but packed in I? Actually I=4, B=1) -> use: I B H 32s
REQUEST_FMT = "!IBB32s"      # cookie, type, rounds, name
PAYLOAD_FMT = "!IB5sB3s"     # cookie, type, decision(5), result(1), card(3)
CARD_FMT = "!HB"             # rank(2), suit(1) => total 3 bytes

OFFER_LEN = struct.calcsize(OFFER_FMT)
REQUEST_LEN = struct.calcsize(REQUEST_FMT)
PAYLOAD_LEN = struct.calcsize(PAYLOAD_FMT)


def _pad_fixed(s: str, length: int) -> bytes:
    b = s.encode("utf-8", errors="ignore")[:length]
    return b + b"\x00" * (length - len(b))


def _unpad_fixed(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")


@dataclass
class Offer:
    tcp_port: int
    server_name: str


@dataclass
class Request:
    rounds: int
    team_name: str


@dataclass
class Payload:
    decision: bytes  # exactly 5 bytes, e.g. b"Hittt" or b"Stand" (client->server)
    result: int      # 0/1/2/3 (server->client)
    card_rank: int   # 0 if none
    card_suit: int   # 0..3 (HDCS) ; 0 if none


def pack_offer(tcp_port: int, server_name: str) -> bytes:
    if not (0 <= tcp_port <= 65535):
        raise ValueError("tcp_port out of range")
    name_b = _pad_fixed(server_name, NAME_LEN)
    # cookie (I), type (B), port (H), name (32s)
    return struct.pack("!IBH32s", MAGIC_COOKIE, MSG_OFFER, tcp_port, name_b)


def unpack_offer(data: bytes) -> Offer:
    if len(data) < struct.calcsize("!IBH32s"):
        raise ValueError("offer too short")
    cookie, mtype, tcp_port, name_b = struct.unpack("!IBH32s", data[:struct.calcsize("!IBH32s")])
    if cookie != MAGIC_COOKIE or mtype != MSG_OFFER:
        raise ValueError("invalid offer")
    return Offer(tcp_port=tcp_port, server_name=_unpad_fixed(name_b))


def pack_request(rounds: int, team_name: str) -> bytes:
    if not (1 <= rounds <= 255):
        raise ValueError("rounds must be 1..255")
    name_b = _pad_fixed(team_name, NAME_LEN)
    return struct.pack("!IBB32s", MAGIC_COOKIE, MSG_REQUEST, rounds, name_b)


def unpack_request(data: bytes) -> Request:
    if len(data) < struct.calcsize("!IBB32s"):
        raise ValueError("request too short")
    cookie, mtype, rounds, name_b = struct.unpack("!IBB32s", data[:struct.calcsize("!IBB32s")])
    if cookie != MAGIC_COOKIE or mtype != MSG_REQUEST:
        raise ValueError("invalid request")
    return Request(rounds=rounds, team_name=_unpad_fixed(name_b))


def pack_card(rank: int, suit: int) -> bytes:
    if not (0 <= rank <= 13):
        raise ValueError("rank must be 0..13 (0 means none)")
    if not (0 <= suit <= 3):
        raise ValueError("suit must be 0..3")
    return struct.pack(CARD_FMT, rank, suit)


def unpack_card(card3: bytes) -> tuple[int, int]:
    if len(card3) != CARD_LEN:
        raise ValueError("card must be exactly 3 bytes")
    return struct.unpack(CARD_FMT, card3)


def pack_payload_client(decision_text: str) -> bytes:
    # client sends "Hittt" or "Stand"
    if decision_text not in ("Hittt", "Stand"):
        raise ValueError("decision must be 'Hittt' or 'Stand'")
    decision = decision_text.encode("ascii")
    decision = decision[:DECISION_LEN].ljust(DECISION_LEN, b"\x00")
    return struct.pack(PAYLOAD_FMT, MAGIC_COOKIE, MSG_PAYLOAD, decision, 0, b"\x00" * CARD_LEN)


def pack_payload_server(result: int, rank: int, suit: int) -> bytes:
    card3 = pack_card(rank, suit)
    return struct.pack(PAYLOAD_FMT, MAGIC_COOKIE, MSG_PAYLOAD, b"\x00" * DECISION_LEN, result, card3)


def unpack_payload(data: bytes) -> Payload:
    if len(data) < struct.calcsize(PAYLOAD_FMT):
        raise ValueError("payload too short")
    cookie, mtype, decision, result, card3 = struct.unpack(PAYLOAD_FMT, data[:struct.calcsize(PAYLOAD_FMT)])
    if cookie != MAGIC_COOKIE or mtype != MSG_PAYLOAD:
        raise ValueError("invalid payload")
    rank, suit = unpack_card(card3)
    return Payload(decision=decision, result=result, card_rank=rank, card_suit=suit)
