# tests.py
from utils.messages import (
    pack_offer, unpack_offer,
    pack_request, unpack_request,
    pack_payload_client, unpack_payload,
    pack_payload_server
)

def main():
    o = unpack_offer(pack_offer(5555, "MyServer"))
    assert o.tcp_port == 5555 and o.server_name == "MyServer"

    r = unpack_request(pack_request(7, "Team66"))
    assert r.rounds == 7 and r.team_name == "Team66"

    p = unpack_payload(pack_payload_client("Hittt"))
    assert p.decision.startswith(b"Hittt")

    p2 = unpack_payload(pack_payload_server(3, 13, 0))
    assert p2.result == 3 and p2.card_rank == 13 and p2.card_suit == 0

    print("OK: protocol packing/unpacking works")

if __name__ == "__main__":
    main()
