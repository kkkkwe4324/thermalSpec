"""Local wire-size probe; does not measure phone/Orin network latency."""
import json
import struct
import time


def main():
    vocabulary = 151665  # Shared tokenizer IDs after masking padded model logits.
    proposals = 4
    print(f"dense_q_fp32_bytes_per_round={vocabulary * 4 * proposals}")
    for support_size in (32, 128, 512):
        sparse = [[token, 1 / support_size] for token in range(support_size)]
        packet = {"proposals": [{"token_id": i, "q_support": sparse} for i in range(proposals)]}
        start = time.perf_counter()
        for _ in range(1000):
            encoded = json.dumps(packet, separators=(",", ":")).encode("utf-8")
        elapsed_ms = (time.perf_counter() - start) * 1000 / 1000
        binary_floor = proposals * (2 + support_size * struct.calcsize("<If"))
        print(f"support={support_size} sparse_json_bytes={len(encoded)} "
              f"sparse_binary_floor_bytes={binary_floor} local_json_encode_ms={elapsed_ms:.3f}")


if __name__ == "__main__":
    main()
