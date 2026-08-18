#!/usr/bin/env python3
"""
Detection-only inspector for AI-provenance / watermark signals.

This script NEVER modifies, strips, or rewrites the target file. It only
reads and reports. See ../SKILL.md for the detection layers and their
limitations.
"""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Layer 1: hidden/anomalous Unicode often used as invisible watermark channels
# ---------------------------------------------------------------------------

SUSPICIOUS_UNICODE = {
    0x200B: "ZERO WIDTH SPACE",
    0x200C: "ZERO WIDTH NON-JOINER",
    0x200D: "ZERO WIDTH JOINER",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
    0x2060: "WORD JOINER",
    0x2061: "FUNCTION APPLICATION",
    0x2062: "INVISIBLE TIMES",
    0x2063: "INVISIBLE SEPARATOR",
    0x2064: "INVISIBLE PLUS",
    0xFEFF: "ZERO WIDTH NO-BREAK SPACE (BOM)",
    0x00AD: "SOFT HYPHEN",
    0x061C: "ARABIC LETTER MARK",
    0x202A: "LEFT-TO-RIGHT EMBEDDING",
    0x202B: "RIGHT-TO-LEFT EMBEDDING",
    0x202C: "POP DIRECTIONAL FORMATTING",
    0x202D: "LEFT-TO-RIGHT OVERRIDE",
    0x202E: "RIGHT-TO-LEFT OVERRIDE",
    0x2066: "LEFT-TO-RIGHT ISOLATE",
    0x2067: "RIGHT-TO-LEFT ISOLATE",
    0x2068: "FIRST STRONG ISOLATE",
    0x2069: "POP DIRECTIONAL ISOLATE",
}

EXOTIC_SPACES = {
    0x00A0: "NO-BREAK SPACE",
    0x1680: "OGHAM SPACE MARK",
    0x2000: "EN QUAD",
    0x2001: "EM QUAD",
    0x2002: "EN SPACE",
    0x2003: "EM SPACE",
    0x2004: "THREE-PER-EM SPACE",
    0x2005: "FOUR-PER-EM SPACE",
    0x2006: "SIX-PER-EM SPACE",
    0x2007: "FIGURE SPACE",
    0x2008: "PUNCTUATION SPACE",
    0x2009: "THIN SPACE",
    0x200A: "HAIR SPACE",
    0x202F: "NARROW NO-BREAK SPACE",
    0x205F: "MEDIUM MATHEMATICAL SPACE",
    0x3000: "IDEOGRAPHIC SPACE",
}

TAG_CHAR_START = 0xE0000
TAG_CHAR_END = 0xE007F


def classify_codepoint(cp):
    if cp in SUSPICIOUS_UNICODE:
        return "invisible/formatting", SUSPICIOUS_UNICODE[cp]
    if cp in EXOTIC_SPACES:
        return "exotic space", EXOTIC_SPACES[cp]
    if TAG_CHAR_START <= cp <= TAG_CHAR_END:
        return "unicode tag character", f"TAG CHAR U+{cp:04X} (hidden-signaling range)"
    return None, None


def scan_text_unicode(text):
    hits = []
    counts = {}
    line = 1
    col = 0
    for i, ch in enumerate(text):
        if ch == "\n":
            line += 1
            col = 0
            continue
        col += 1
        cp = ord(ch)
        category, label = classify_codepoint(cp)
        if category:
            counts[label] = counts.get(label, 0) + 1
            if len(hits) < 50:
                hits.append({
                    "codepoint": f"U+{cp:04X}",
                    "name": label,
                    "category": category,
                    "line": line,
                    "col": col,
                })
    return hits, counts


def inspect_text_payload(text):
    hits, counts = scan_text_unicode(text)
    result = {
        "layer": "text_unicode",
        "signals_found": len(hits) > 0,
        "occurrence_counts": counts,
        "sample_occurrences": hits,
        "note": (
            "This only detects hidden/invisible Unicode channels. It cannot detect "
            "statistical token-sampling watermarks (e.g. SynthID-Text, KGW-family "
            "schemes) — those require the vendor's secret key/model. Treat the "
            "absence of a hit here as inconclusive for that class of watermark, "
            "not as proof the text is unwatermarked. Use an official vendor "
            "verifier for an authoritative check."
        ),
    }
    if hits:
        result["classification"] = "signals_found"
    else:
        result["classification"] = "no_unicode_signals_found"
    return result


# ---------------------------------------------------------------------------
# Layer 2: raw-byte signature scan (works on any file, used as a fallback and
# as a cross-check for containers we don't have a parser library for)
# ---------------------------------------------------------------------------

SIGNATURE_STRINGS = [
    b"C2PA", b"urn:c2pa", b"jumb", b"c2pa.", b"cai:", b"ai_generated",
    b"SynthID", b"Firefly", b"Adobe Firefly", b"Midjourney", b"DALL-E",
    b"DALL\xc2\xb7E", b"Stable Diffusion", b"stability.ai", b"Runway", b"Sora",
    b"Claude", b"Anthropic", b"Gemini", b"Google AI", b"Bard",
    b"generative-ai", b"GenAI", b"NovelAI", b"Leonardo.Ai",
]


def scan_raw_bytes(data):
    found = {}
    for sig in SIGNATURE_STRINGS:
        idx = data.find(sig)
        if idx != -1:
            found[sig.decode("utf-8", "replace")] = idx
    return found


# ---------------------------------------------------------------------------
# Layer 3: image metadata (EXIF/XMP/IPTC)
# ---------------------------------------------------------------------------

def inspect_image(path, raw):
    result = {"layer": "image_metadata", "signals_found": False, "details": {}}
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(path)
        exif_data = {}
        exif = getattr(img, "_getexif", lambda: None)()
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[str(tag)] = str(value)[:200]
        xmp = img.info.get("xmp")
        if xmp:
            exif_data["XMP_present"] = True
            exif_data["XMP_excerpt"] = xmp[:500] if isinstance(xmp, str) else str(xmp[:500])
        result["details"]["exif"] = exif_data
        result["details"]["pillow_available"] = True
    except ImportError:
        result["details"]["pillow_available"] = False
        result["details"]["note"] = "Pillow not installed; falling back to raw byte scan only."
    except Exception as e:
        result["details"]["error"] = str(e)

    sig_hits = scan_raw_bytes(raw)
    if sig_hits:
        result["details"]["raw_signature_hits"] = sig_hits
        result["signals_found"] = True

    metadata_text = json.dumps(result["details"].get("exif", {}))
    for sig in SIGNATURE_STRINGS:
        if sig.decode("utf-8", "replace") in metadata_text:
            result["signals_found"] = True

    has_c2pa_marker = any(k.lower().startswith(("c2pa", "urn:c2pa", "jumb", "cai")) for k in sig_hits)
    result["c2pa_manifest_marker_present"] = has_c2pa_marker
    result["classification"] = "signals_found" if result["signals_found"] else "no_signals_found"
    return result


# ---------------------------------------------------------------------------
# Layer 4: PDF /Info + XMP
# ---------------------------------------------------------------------------

def inspect_pdf(path, raw):
    result = {"layer": "pdf_metadata", "signals_found": False, "details": {}}
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        meta = reader.metadata or {}
        info = {k: str(v) for k, v in meta.items()} if meta else {}
        result["details"]["info_dict"] = info
        result["details"]["pypdf_available"] = True
    except ImportError:
        result["details"]["pypdf_available"] = False
        result["details"]["note"] = "pypdf not installed; falling back to raw byte scan only."
    except Exception as e:
        result["details"]["error"] = str(e)

    sig_hits = scan_raw_bytes(raw)
    if sig_hits:
        result["details"]["raw_signature_hits"] = sig_hits
        result["signals_found"] = True

    info_text = json.dumps(result["details"].get("info_dict", {}))
    for sig in SIGNATURE_STRINGS:
        if sig.decode("utf-8", "replace") in info_text:
            result["signals_found"] = True

    result["classification"] = "signals_found" if result["signals_found"] else "no_signals_found"
    return result


# ---------------------------------------------------------------------------
# Layer 5: OOXML (docx/xlsx/pptx) core.xml / app.xml properties
# ---------------------------------------------------------------------------

def inspect_ooxml(path):
    result = {"layer": "ooxml_properties", "signals_found": False, "details": {}}
    try:
        with zipfile.ZipFile(path) as z:
            for member in ("docProps/core.xml", "docProps/app.xml"):
                if member in z.namelist():
                    content = z.read(member).decode("utf-8", "replace")
                    result["details"][member] = content[:1000]
                    for sig in SIGNATURE_STRINGS:
                        if sig.decode("utf-8", "replace") in content:
                            result["signals_found"] = True
    except Exception as e:
        result["details"]["error"] = str(e)

    result["classification"] = "signals_found" if result["signals_found"] else "no_signals_found"
    return result


# ---------------------------------------------------------------------------
# Layer 6: audio/video embedded metadata
# ---------------------------------------------------------------------------

def inspect_media(path, raw):
    result = {"layer": "media_metadata", "signals_found": False, "details": {}}
    inspected = False
    try:
        import mutagen

        f = mutagen.File(str(path))
        if f is not None:
            tags = {str(k): str(v)[:200] for k, v in (f.tags or {}).items()} if f.tags else {}
            result["details"]["tags"] = tags
            inspected = True
            tags_text = json.dumps(tags)
            for sig in SIGNATURE_STRINGS:
                if sig.decode("utf-8", "replace") in tags_text:
                    result["signals_found"] = True
    except ImportError:
        result["details"]["mutagen_available"] = False
    except Exception as e:
        result["details"]["mutagen_error"] = str(e)

    if not inspected:
        import shutil
        import subprocess

        if shutil.which("ffprobe"):
            try:
                out = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_format", "-show_streams", str(path)],
                    capture_output=True, text=True, timeout=30,
                )
                result["details"]["ffprobe"] = json.loads(out.stdout) if out.stdout else {}
                inspected = True
                probe_text = out.stdout
                for sig in SIGNATURE_STRINGS:
                    if sig.decode("utf-8", "replace") in probe_text:
                        result["signals_found"] = True
            except Exception as e:
                result["details"]["ffprobe_error"] = str(e)
        else:
            result["details"]["note"] = "Neither mutagen nor ffprobe available; media not inspected."

    sig_hits = scan_raw_bytes(raw[:2_000_000])
    if sig_hits:
        result["details"]["raw_signature_hits"] = sig_hits
        result["signals_found"] = True

    if not inspected and not sig_hits:
        result["classification"] = "inconclusive_missing_dependency"
    elif result["signals_found"]:
        result["classification"] = "signals_found"
    else:
        result["classification"] = "no_signals_found"
    return result


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif", ".avif", ".tif", ".tiff", ".bmp", ".gif"}
PDF_EXT = {".pdf"}
OOXML_EXT = {".docx", ".xlsx", ".pptx"}
MEDIA_EXT = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mov", ".m4v", ".webm", ".mkv"}
TEXT_EXT = {".txt", ".md", ".markdown", ".csv", ".json", ".yaml", ".yml", ".html", ".htm", ".xml", ".rst"}


def inspect_file(path_str):
    path = Path(path_str)
    report = {"file": str(path), "exists": path.exists()}
    if not path.exists() or not path.is_file():
        report["error"] = "File not found or not a regular file."
        return report

    raw = path.read_bytes()
    ext = path.suffix.lower()
    layers = []

    if ext in OOXML_EXT:
        layers.append(inspect_ooxml(path))
    elif ext in PDF_EXT:
        layers.append(inspect_pdf(path, raw))
    elif ext in IMAGE_EXT:
        layers.append(inspect_image(path, raw))
    elif ext in MEDIA_EXT:
        layers.append(inspect_media(path, raw))
    elif ext in TEXT_EXT or _looks_like_text(raw):
        try:
            text = raw.decode("utf-8")
            layers.append(inspect_text_payload(text))
        except UnicodeDecodeError:
            layers.append({"layer": "text_unicode", "classification": "not_applicable",
                            "note": "File is not valid UTF-8 text."})
    else:
        sig_hits = scan_raw_bytes(raw)
        layers.append({
            "layer": "raw_signature_scan",
            "signals_found": bool(sig_hits),
            "details": {"raw_signature_hits": sig_hits},
            "classification": "signals_found" if sig_hits else "no_signals_found",
            "note": f"Unrecognized extension '{ext}'; only a raw byte signature scan was run.",
        })

    report["layers"] = layers
    any_signal = any(l.get("classification") == "signals_found" for l in layers)
    any_inconclusive = any(l.get("classification") == "inconclusive_missing_dependency" for l in layers)
    if any_signal:
        report["overall"] = "signals_found"
    elif any_inconclusive:
        report["overall"] = "inconclusive"
    else:
        report["overall"] = "no_signals_found"
    return report


def _looks_like_text(raw, sample_size=4096):
    sample = raw[:sample_size]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Detection-only scan for AI-provenance/watermark signals. Never modifies files."
    )
    parser.add_argument("paths", nargs="+", help="File(s) to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()

    reports = [inspect_file(p) for p in args.paths]

    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
        return

    for report in reports:
        print(f"\n=== {report['file']} ===")
        if report.get("error"):
            print(f"  ERROR: {report['error']}")
            continue
        print(f"  Overall: {report['overall']}")
        for layer in report["layers"]:
            print(f"  - [{layer['layer']}] {layer.get('classification', 'n/a')}")
            if layer.get("note"):
                print(f"      note: {layer['note']}")
            if layer.get("details", {}).get("raw_signature_hits"):
                print(f"      raw signature hits: {layer['details']['raw_signature_hits']}")
            if layer.get("occurrence_counts"):
                print(f"      unicode signal counts: {layer['occurrence_counts']}")


if __name__ == "__main__":
    main()
