# utils/constants.py

MAGIC_COOKIE = 0xabcddcba

# Message types
MSG_OFFER = 0x2
MSG_REQUEST = 0x3
MSG_PAYLOAD = 0x4

# Payload (server -> client) round result
RESULT_NOT_OVER = 0x0
RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3

# Networking
UDP_OFFER_PORT = 13122
OFFER_INTERVAL_SEC = 1

# Fixed sizes
NAME_LEN = 32
DECISION_LEN = 5
CARD_LEN = 3
