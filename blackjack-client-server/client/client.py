# client/client.py
import socket

from constants import UDP_OFFER_PORT
from messages import (
    unpack_offer,
    pack_request,
    PAYLOAD_LEN,
    unpack_payload,
    pack_payload_client,
)
from utils.sockets import recv_exact

TEAM_NAME = "BlackCrown_ormoa"


def update_stats(result: int, wins: int, losses: int, ties: int):
    # result: 3 win, 2 loss, 1 tie, 0 not over
    if result == 3:
        wins += 1
    elif result == 2:
        losses += 1
    elif result == 1:
        ties += 1
    return wins, losses, ties


def main():
    # UDP socket created once, client runs forever
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    udp_sock.bind(("", UDP_OFFER_PORT))

    print("Client started, listening for offer requests...")

    while True:
        # session settings
        try:
            rounds = int(input("Enter number of rounds (1-255): ").strip())
        except ValueError:
            print("Invalid input. Must be a number 1..255")
            continue

        if not (1 <= rounds <= 255):
            print("Invalid rounds. Must be 1..255")
            continue

        wins = 0
        losses = 0
        ties = 0

        # wait for an offer
        while True:
            data, addr = udp_sock.recvfrom(2048)
            server_ip = addr[0]

            try:
                offer = unpack_offer(data)
            except Exception:
                continue

            # NOTE: to be compatible with other teams, do NOT filter by server name
            print(f"Received offer from {server_ip} (server name: {offer.server_name}, tcp port: {offer.tcp_port})")

            # connect TCP and play session
            tcp_sock = None
            try:
                tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_sock.settimeout(5)
                tcp_sock.connect((server_ip, offer.tcp_port))

                req = pack_request(rounds, TEAM_NAME)
                tcp_sock.sendall(req)
                print("Sent request over TCP.")

                # ACK
                ack = tcp_sock.recv(1)
                if ack != b"\x01":
                    print("No ACK (unexpected). Trying next offer...")
                    tcp_sock.close()
                    continue

                print("Server ACK received.")
                tcp_sock.settimeout(None)  # interactive play

                for round_i in range(1, rounds + 1):
                    print(f"--- Round {round_i} ---")

                    # initial deal: 3 payloads
                    for _ in range(3):
                        p = unpack_payload(recv_exact(tcp_sock, PAYLOAD_LEN))
                        print(f"Got card rank={p.card_rank} suit={p.card_suit} result={p.result}")

                    # player turn
                    while True:
                        choice = input("Hit or Stand? ").strip().lower()

                        if choice == "hit":
                            tcp_sock.sendall(pack_payload_client("Hittt"))
                            resp = unpack_payload(recv_exact(tcp_sock, PAYLOAD_LEN))

                            if resp.result != 0:
                                # round ended (bust or final)
                                wins, losses, ties = update_stats(resp.result, wins, losses, ties)
                                if resp.result == 3:
                                    print("Result: WIN")
                                elif resp.result == 2:
                                    print("Result: LOSS")
                                elif resp.result == 1:
                                    print("Result: TIE")
                                break

                            print(f"Got card rank={resp.card_rank} suit={resp.card_suit}")
                            continue

                        elif choice == "stand":
                            tcp_sock.sendall(pack_payload_client("Stand"))
                            print("Stand sent. Dealer turn:")

                            # dealer may send multiple cards, then final result
                            while True:
                                resp = unpack_payload(recv_exact(tcp_sock, PAYLOAD_LEN))

                                if resp.card_rank != 0:
                                    print(f"Dealer card: rank={resp.card_rank} suit={resp.card_suit}")

                                if resp.result != 0:
                                    wins, losses, ties = update_stats(resp.result, wins, losses, ties)
                                    if resp.result == 3:
                                        print("Result: WIN")
                                    elif resp.result == 2:
                                        print("Result: LOSS")
                                    elif resp.result == 1:
                                        print("Result: TIE")
                                    break

                            break

                        else:
                            print("Please type: Hit or Stand")

                tcp_sock.close()

                played = wins + losses + ties
                win_rate = (wins / played) if played > 0 else 0.0
                print(f"Finished playing {played} rounds, win rate: {win_rate:.2f}")

                # session finished successfully -> go ask for rounds again
                break

            except Exception as e:
                print(f"TCP connection failed: {e}")
                try:
                    if tcp_sock:
                        tcp_sock.close()
                except Exception:
                    pass
                print("Waiting for a new offer...")
                # go back to waiting offers
                continue


if __name__ == "__main__":
    main()
