# server/server.py
import socket
import threading
import time

from protocol.constants import UDP_OFFER_PORT, OFFER_INTERVAL_SEC
from protocol.messages import pack_offer, unpack_request
from protocol.messages import REQUEST_LEN
from utils.sockets import recv_exact
from protocol.cards import Deck
from protocol.messages import PAYLOAD_LEN, pack_payload_server
from protocol.cards import card_value
from protocol.messages import unpack_payload
from protocol.constants import RESULT_NOT_OVER, RESULT_LOSS, RESULT_WIN, RESULT_TIE




TEAM_NAME = "BlackCrown_ormoa"


def udp_offer_loop(tcp_port: int):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f"Server started, listening on TCP port {tcp_port}")
    while True:
        try:
            msg = pack_offer(tcp_port, TEAM_NAME)
            udp_sock.sendto(msg, ("<broadcast>", UDP_OFFER_PORT))
            time.sleep(OFFER_INTERVAL_SEC)
        except Exception as e:
            print(f"Error sending offer: {e}")
            time.sleep(OFFER_INTERVAL_SEC)


def handle_client(conn: socket.socket, addr):
    try:
        conn.settimeout(5)

        data = recv_exact(conn, REQUEST_LEN)
        req = unpack_request(data)

        print(f"Accepted connection from {addr[0]}:{addr[1]} | team={req.team_name} | rounds={req.rounds}")

        # ACK
        conn.sendall(b"\x01")
        conn.settimeout(None)

        for round_i in range(1, req.rounds + 1):
            print(f"--- Round {round_i} ---")

            deck = Deck()

            # player cards
            p1 = deck.draw()
            p2 = deck.draw()

            # dealer cards (second is hidden for now)
            d1 = deck.draw()
            d2_hidden = deck.draw()

            dealer_sum = card_value(d1.rank) + card_value(d2_hidden.rank)

            # send 2 player cards + 1 dealer open card
            conn.sendall(pack_payload_server(RESULT_NOT_OVER, p1.rank, p1.suit))
            conn.sendall(pack_payload_server(RESULT_NOT_OVER, p2.rank, p2.suit))
            conn.sendall(pack_payload_server(RESULT_NOT_OVER, d1.rank, d1.suit))

            print(f"Sent player cards: ({p1.rank},{p1.suit}), ({p2.rank},{p2.suit}) | dealer open: ({d1.rank},{d1.suit})")

            player_sum = card_value(p1.rank) + card_value(p2.rank)

            # Player turn loop
            while True:
                # read decision payload from client
                decision_bytes = recv_exact(conn, PAYLOAD_LEN)
                p = unpack_payload(decision_bytes)
                decision = p.decision.rstrip(b"\x00").decode("ascii", errors="ignore")

                if decision == "Hittt":
                    c = deck.draw()
                    player_sum += card_value(c.rank)
                    print(f"Player hit -> ({c.rank},{c.suit}) sum={player_sum}")

                    if player_sum > 21:
                        # player busts -> immediate loss
                        conn.sendall(pack_payload_server(RESULT_LOSS, 0, 0))
                        print("Player bust -> dealer wins")
                        break
                    else:
                        conn.sendall(pack_payload_server(RESULT_NOT_OVER, c.rank, c.suit))


                elif decision == "Stand":

                    print(f"Player stand with sum={player_sum}")

                    # 1) reveal hidden dealer card

                    conn.sendall(pack_payload_server(RESULT_NOT_OVER, d2_hidden.rank, d2_hidden.suit))

                    print(f"Dealer reveals -> ({d2_hidden.rank},{d2_hidden.suit}) sum={dealer_sum}")

                    # 2) dealer draws until sum >= 17 or bust

                    while dealer_sum < 17:
                        c = deck.draw()

                        dealer_sum += card_value(c.rank)

                        conn.sendall(pack_payload_server(RESULT_NOT_OVER, c.rank, c.suit))

                        print(f"Dealer hit -> ({c.rank},{c.suit}) sum={dealer_sum}")

                    # 3) decide winner

                    if dealer_sum > 21:

                        result = RESULT_WIN

                        print("Dealer bust -> player wins")

                    else:

                        if player_sum > dealer_sum:

                            result = RESULT_WIN

                            print("Player higher -> player wins")

                        elif dealer_sum > player_sum:

                            result = RESULT_LOSS

                            print("Dealer higher -> dealer wins")

                        else:

                            result = RESULT_TIE

                            print("Tie")

                    # 4) send final result payload (card=0)

                    conn.sendall(pack_payload_server(result, 0, 0))

                    break

                else:
                    # החלטה לא תקינה -> נסיים חיבור/round
                    print(f"Invalid decision from client: {decision!r}")
                    conn.sendall(pack_payload_server(RESULT_LOSS, 0, 0))
                    break

        conn.close()

    except Exception as e:
        print(f"Client {addr} error: {e}")
        try:
            conn.close()
        except Exception:
            pass




def main():
    # TCP listen socket
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind(("", 0))  # 0 = choose random free port
    tcp_sock.listen()

    tcp_port = tcp_sock.getsockname()[1]

    # UDP offers thread
    threading.Thread(target=udp_offer_loop, args=(tcp_port,), daemon=True).start()

    # Accept loop
    while True:
        try:
            conn, addr = tcp_sock.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            break


if __name__ == "__main__":
    main()
