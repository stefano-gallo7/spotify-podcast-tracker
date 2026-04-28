import json
import glob
import os
import argparse


def parse_podcast_history(source_folder: str, output_path: str = "data/podcast_history.json", min_seconds: int = 40) -> list[dict]:
    """
    Parse Spotify extended streaming history files and extract podcast episodes.

    Reads all Streaming_History_Audio_*.json files from source_folder, filters for
    podcast episodes, deduplicates by episode URI (keeping the longest listen; ties broken by most recent ts),
    and saves the result to output_path.
    """
    pattern = os.path.join(source_folder, "Streaming_History_Audio_*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No streaming history files found in: {source_folder}")
        return []

    print(f"Found {len(files)} file(s): {[os.path.basename(f) for f in files]}")

    raw_episodes: list[dict] = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
        episodes = [e for e in entries if e.get("spotify_episode_uri")]
        print(f"  {os.path.basename(path)}: {len(episodes)} podcast events")
        raw_episodes.extend(episodes)

    print(f"\n{len(raw_episodes)} total podcast play events")

    min_ms = min_seconds * 1000
    raw_episodes = [e for e in raw_episodes if e["ms_played"] >= min_ms]
    print(f"{len(raw_episodes)} events after filtering plays shorter than {min_seconds}s")


    # Deduplicate by episode URI, keeping the longest listen; break ties by most recent ts
    by_uri: dict[str, dict] = {}
    for episode in raw_episodes:
        uri = episode["spotify_episode_uri"]
        if uri not in by_uri:
            by_uri[uri] = episode
        else:
            current = by_uri[uri]
            if (episode["ms_played"], episode["ts"]) > (current["ms_played"], current["ts"]):
                by_uri[uri] = episode

    deduplicated = sorted(by_uri.values(), key=lambda e: e["ts"], reverse=True)
    print(f"{len(deduplicated)} unique episodes after deduplication")

    output = [_extract_fields(e) for e in deduplicated]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_path}")
    return output


def _extract_fields(entry: dict) -> dict:
    return {
        "listened_at": entry["ts"],
        "show_name": entry["episode_show_name"],
        "episode_name": entry["episode_name"],
        "spotify_episode_uri": entry["spotify_episode_uri"],
        "ms_played": entry["ms_played"],
        "skipped": entry["skipped"],
        "reason_end": entry["reason_end"],
        "offline": entry["offline"],
        "offline_timestamp": entry["offline_timestamp"],
        "platform": entry["platform"],
        "connection_country": entry["conn_country"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse Spotify extended streaming history and extract podcast episodes."
    )
    parser.add_argument(
        "source_folder",
        help="Folder containing Spotify's Streaming_History_Audio_*.json files",
    )
    parser.add_argument(
        "--output",
        default="data/podcast_history.json",
        metavar="PATH",
        help="Output JSON file path (default: data/podcast_history.json)",
    )

    parser.add_argument(
        "--min-seconds",
        type=int,
        default=40,
        metavar="N",
        help="Exclude episodes played for less than N seconds (default: 40)",
    )

    args = parser.parse_args()
    parse_podcast_history(args.source_folder, args.output, args.min_seconds)
