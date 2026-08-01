from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .utils import read_json, write_json


MANIFEST_NAME = "artifact_manifest.json"
OUTPUT_ARTIFACTS = (
    "demo_dashboard.html",
    "demo_report.md",
    "demo_trace.json",
    "escalation_packet.json",
    "post_training_bundle.json",
    "provenance_bundle.json",
    "ranked_candidates.json",
    "retrieved_sources.json",
    "trace_to_reward_sample.json",
    "validation_scorecard.json",
)


class ArtifactIntegrityError(ValueError):
    """Raised when a run manifest is unsafe, incomplete, or does not match disk."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifact(root: Path, relative_path: str) -> Path:
    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or ".." in pure_path.parts or relative_path in {"", "."}:
        raise ArtifactIntegrityError(f"unsafe artifact path: {relative_path!r}")
    resolved_root = root.resolve()
    resolved_path = (root / Path(*pure_path.parts)).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ArtifactIntegrityError(f"artifact escapes output directory: {relative_path!r}")
    return resolved_path


def build_artifact_manifest(
    output_dir: Path,
    trace_id: str,
    artifact_paths: Iterable[str] = OUTPUT_ARTIFACTS,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative_path in sorted(artifact_paths):
        if relative_path in seen:
            raise ArtifactIntegrityError(f"duplicate artifact path: {relative_path}")
        seen.add(relative_path)
        path = _resolve_artifact(output_dir, relative_path)
        if not path.is_file():
            raise ArtifactIntegrityError(f"missing artifact: {relative_path}")
        entries.append(
            {
                "path": relative_path,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": "1.0",
        "trace_id": trace_id,
        "hash_algorithm": "sha256",
        "files": entries,
    }


def write_artifact_manifest(output_dir: Path, trace_id: str) -> Path:
    manifest_path = output_dir / MANIFEST_NAME
    write_json(manifest_path, build_artifact_manifest(output_dir, trace_id))
    return manifest_path


def verify_artifact_manifest(output_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    manifest_path = manifest_path or output_dir / MANIFEST_NAME
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise ArtifactIntegrityError("unsupported or malformed artifact manifest")
    if manifest.get("hash_algorithm") != "sha256":
        raise ArtifactIntegrityError("artifact manifest must use sha256")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ArtifactIntegrityError("artifact manifest has no files")

    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ArtifactIntegrityError("artifact manifest contains a malformed entry")
        relative_path = entry["path"]
        if relative_path in seen:
            raise ArtifactIntegrityError(f"duplicate artifact path: {relative_path}")
        seen.add(relative_path)
        path = _resolve_artifact(output_dir, relative_path)
        if not path.is_file():
            raise ArtifactIntegrityError(f"missing artifact: {relative_path}")
        actual_size = path.stat().st_size
        if entry.get("bytes") != actual_size:
            raise ArtifactIntegrityError(
                f"size mismatch for {relative_path}: expected {entry.get('bytes')}, got {actual_size}"
            )
        actual_hash = sha256_file(path)
        if entry.get("sha256") != actual_hash:
            raise ArtifactIntegrityError(f"sha256 mismatch for {relative_path}")

    return {
        "trace_id": manifest.get("trace_id"),
        "verified_files": len(files),
        "manifest": str(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a SciTrace-RL output artifact manifest.")
    parser.add_argument("output_dir", type=Path, help="Directory produced by scitrace-rl.")
    parser.add_argument("--manifest", type=Path, help="Optional manifest path; defaults inside output_dir.")
    args = parser.parse_args()
    try:
        result = verify_artifact_manifest(args.output_dir, args.manifest)
    except (ArtifactIntegrityError, OSError, ValueError) as exc:
        raise SystemExit(f"artifact verification failed: {exc}") from exc
    print(
        f"verified {result['verified_files']} artifacts "
        f"for trace {result['trace_id']}"
    )


if __name__ == "__main__":
    main()
