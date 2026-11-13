"""Freeze a small, reproducible real-user prompt workload from WildChat-1M."""
import argparse
import hashlib
import json
import random
import time
from bisect import bisect_right
from collections import Counter
from pathlib import Path

from .core.config import load_project


def locate_row(index, shard_starts, group_starts):
    shard = bisect_right(shard_starts, index) - 1
    if shard < 0 or shard >= len(group_starts):
        raise IndexError(index)
    within_shard = index - shard_starts[shard]
    group = bisect_right(group_starts[shard], within_shard) - 1
    return shard, group, within_shard - group_starts[shard][group]


def pinned_pages(source, starts):
    """Read only selected Parquet row groups at the exact source commit."""
    import pyarrow.parquet as parquet
    from huggingface_hub import HfFileSystem

    fs = HfFileSystem()
    base = f"datasets/{source['source_repo']}@{source['source_revision']}/data/"
    paths = [base + f"train-{index:05d}-of-{source['source_shards']:05d}.parquet"
             for index in range(source["source_shards"])]
    shard_starts = [0]
    group_starts = []
    for path in paths:
        with fs.open(path, "rb") as stream:
            metadata = parquet.ParquetFile(stream).metadata
        groups = [0]
        for index in range(metadata.num_row_groups):
            groups.append(groups[-1] + metadata.row_group(index).num_rows)
        group_starts.append(groups)
        shard_starts.append(shard_starts[-1] + metadata.num_rows)
    if shard_starts[-1] != source["source_row_count"]:
        raise RuntimeError("Pinned WildChat source has a different row count")
    columns = ["conversation_hash", "conversation", "model", "language", "toxic", "redacted"]
    for start in starts:
        page = []
        current_key = None
        group_rows = None
        for row_index in range(start, start + source["selection_page_size"]):
            shard, group, within_group = locate_row(row_index, shard_starts, group_starts)
            if (shard, group) != current_key:
                for attempt in range(3):
                    try:
                        with fs.open(paths[shard], "rb") as stream:
                            group_rows = parquet.ParquetFile(stream).read_row_group(
                                group, columns=columns).to_pylist()
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(0.5 * (attempt + 1))
                current_key = (shard, group)
            page.append((row_index, group_rows[within_group]))
        yield page


def extract_prompt(row):
    if row.get("toxic") or row.get("redacted"):
        return None
    turns = row.get("conversation") or []
    if not turns or turns[0].get("role") != "user":
        return None
    content = turns[0].get("content")
    if not isinstance(content, str) or "\ufffd" in content:
        return None
    return content.strip() or None


def count_prompt_tokens(tokenizer, prompt):
    encoded = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=True, add_generation_prompt=True)
    return len(encoded["input_ids"])


def prepare(project, output):
    from transformers import AutoTokenizer

    source = project["dataset"]
    repo = source["source_repo"]
    revision = source["source_revision"]
    tokenizer = AutoTokenizer.from_pretrained(project["models"]["target"]["hf_repo"],
                                               revision=project["models"]["target"]["revision"])
    rng = random.Random(source["selection_seed"])
    total = source["source_row_count"]
    pages = source["selection_pages"]
    page_size = source["selection_page_size"]
    starts = rng.sample(range(0, total - page_size, page_size), pages)
    candidates = []
    seen = set()
    exclusions = Counter()
    limit = project["generation"]["context_size"] - project["generation"]["formal_max_new_tokens"]
    for page, rows in enumerate(pinned_pages(source, starts), 1):
        for row_index, row in rows:
            prompt = extract_prompt(row)
            if not prompt:
                exclusions["invalid_or_filtered"] += 1
                continue
            if len(prompt) > 12000:
                exclusions["character_length"] += 1
                continue
            content_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            if content_hash in seen:
                exclusions["duplicate"] += 1
                continue
            token_count = count_prompt_tokens(tokenizer, prompt)
            if token_count < 8 or token_count > limit:
                exclusions["token_length"] += 1
                continue
            seen.add(content_hash)
            candidates.append({"prompt_id": f"wildchat-{row_index}",
                               "source_row": row_index,
                               "conversation_hash": row["conversation_hash"],
                               "language": row.get("language"), "source_model": row.get("model"),
                               "prompt_tokens": token_count, "prompt": prompt})
        print(f"Fetched page {page}/{pages}: {len(candidates)} eligible", flush=True)
    needed = sum(source["split_counts"].values())
    if len(candidates) < needed:
        raise RuntimeError(f"Only {len(candidates)} eligible prompts; need {needed}")
    rng.shuffle(candidates)
    chosen = []
    for split in ("calibration", "test"):
        for rank in range(1, source["split_counts"][split] + 1):
            row = candidates.pop()
            chosen.append({"split": split, "selection_rank": rank, **row})
    raw = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                  for row in chosen).encode("utf-8")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    output.write_bytes(raw)
    manifest = {"source_repo": repo, "source_revision_pinned": revision,
                "source_rows_reported": total, "selection_seed": source["selection_seed"],
                "page_starts": starts, "pages": pages, "page_size": page_size,
                "eligible_count": len(candidates) + needed, "excluded": dict(exclusions),
                "selected_count": needed, "sha256": hashlib.sha256(raw).hexdigest(),
                "token_count_min": min(row["prompt_tokens"] for row in chosen),
                "token_count_max": max(row["prompt_tokens"] for row in chosen),
                "languages": dict(Counter(row["language"] for row in chosen))}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    project, _ = load_project()
    print(json.dumps(prepare(project, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
