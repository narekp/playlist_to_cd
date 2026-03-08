import argparse
import os
import sys
import threading

from modes.mp3_cd import run_mp3_pipeline
from modes.audio_cd import run_audio_cd_pipeline


class ConsoleLogger:
    def put(self, message: str) -> None:
        print(message)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run mp3 CD or audio CD post-processing on an existing processed directory."
    )
    parser.add_argument(
        "--mode",
        choices=["mp3", "audio"],
        default="mp3",
        help="Output mode: 'mp3' for MP3 CD pipeline, 'audio' for Audio CD pipeline (default: mp3).",
    )
    parser.add_argument(
        "--processed-dir",
        required=True,
        help="Path to the processed directory containing MP3 files.",
    )
    parser.add_argument(
        "--accepted-duration-sec",
        type=float,
        help="Total accepted duration in seconds (required when --mode mp3).",
    )

    args = parser.parse_args()

    processed_dir = os.path.abspath(args.processed_dir)

    if not os.path.isdir(processed_dir):
        print(f"Error: processed_dir '{processed_dir}' is not a directory or does not exist.", file=sys.stderr)
        sys.exit(1)

    mp3_files = [f for f in os.listdir(processed_dir) if f.lower().endswith(".mp3")]
    if not mp3_files:
        print(f"Error: processed_dir '{processed_dir}' does not contain any .mp3 files.", file=sys.stderr)
        sys.exit(1)

    logger = ConsoleLogger()
    stop_flag = threading.Event()

    try:
        if args.mode == "mp3":
            if args.accepted_duration_sec is None:
                print(
                    "Error: --accepted-duration-sec is required when --mode mp3.",
                    file=sys.stderr,
                )
                sys.exit(1)
            final_size = run_mp3_pipeline(
                processed_dir,
                logger,
                stop_flag,
                args.accepted_duration_sec,
            )
        else:
            final_size = run_audio_cd_pipeline(
                processed_dir,
                logger,
                stop_flag,
            )
    except Exception as exc:
        print(f"Error while running {args.mode} pipeline: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Final size: {final_size:.2f} MB")


if __name__ == "__main__":
    main()
