import json
import glob
import os
import argparse


def parse_podcast_history(source_folder: str, output_path: str = "data/podcast_history.json", min_seconds: int = 40) -> list[dict]:
    """
    Parse Spotify extended streaming history files and aggregate per podcast episode.

    Reads all Streaming_History_Audio_*.json files from source_folder, filters for
    podcast events, drops exact-duplicate events that appear in overlapping export
    files, filters out short plays, then aggregates per episode URI: total ms_played,
    is_fully_played (any reason_end == "trackdone" or "endplay"), last_listened_at, play_count,
    and platform/country from the most recent play.
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

    # Drop exact duplicates (same URI + same timestamp) from overlapping export files
    distinct: dict[tuple[str, str], dict] = {}
    for e in raw_episodes:
        distinct[(e["spotify_episode_uri"], e["ts"])] = e
    plays = list(distinct.values())
    print(f"{len(plays)} distinct play events after dropping exact duplicates")

    min_ms = min_seconds * 1000
    plays = [e for e in plays if e["ms_played"] >= min_ms]
    print(f"{len(plays)} plays after filtering plays shorter than {min_seconds}s")

    # Aggregate per episode URI
    by_uri: dict[str, list[dict]] = {}
    for play in plays:
        by_uri.setdefault(play["spotify_episode_uri"], []).append(play)

    aggregated = [_aggregate(uri, plays) for uri, plays in by_uri.items()]
    aggregated.sort(key=lambda e: e["last_listened_at"], reverse=True)
    print(f"{len(aggregated)} unique episodes after aggregation")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_path}")
    return aggregated


def _aggregate(uri: str, plays: list[dict]) -> dict:
    plays.sort(key=lambda p: p["ts"])
    most_recent = plays[-1]
    return {
        "spotify_episode_uri": uri,
        "show_name": most_recent["episode_show_name"],
        "episode_name": most_recent["episode_name"],
        "ms_played": sum(p["ms_played"] for p in plays),
        "is_fully_played": any(p["reason_end"] in ["trackdone", "endplay"] for p in plays),
        "last_listened_at": most_recent["ts"],
        "play_count": len(plays),
        "platform": most_recent["platform"],
        "connection_country": most_recent["conn_country"],
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
