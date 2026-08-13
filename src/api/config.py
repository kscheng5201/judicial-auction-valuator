import os

# Bind to 0.0.0.0 (not 127.0.0.1) so other devices on the same LAN —
# e.g. a phone on the same Wi-Fi — can reach this. Never expose this
# port directly to the internet without adding auth first.
API_HOST = os.getenv("AUCTION_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("AUCTION_API_PORT", "8000"))
