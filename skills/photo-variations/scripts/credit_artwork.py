#!/usr/bin/env python3
"""Add invisible registry-based credit without image re-encoding.

PNG: a dedicated UTF-8 iTXt chunk. JPEG: a dedicated UTF-8 COM segment.
WebP: one XMP packet, merging a dedicated RDF description when XMP exists.
Existing PNG/JPEG metadata stays byte-exact. Existing WebP XMP fields stay
semantically unchanged; all non-XMP metadata and encoded image chunks stay
byte-exact. Signed, non-UTF-8, or unsafe XMP packets are refused.

Registry: {"schema_version": 1, "workflows": {"route-id": {"creator": "name"}}}.
Run AFTER any metadata cleanup. Attribution is not copyright protection.
Only explicit input/output files are processed; originals are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
import xml.parsers.expat as expat
import zlib
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG_KEY = b"PhotoVariationsCredit"
JPEG_PREFIX = b"PhotoVariationsCredit: "
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
PV_NS = "https://github.com/getinslow/photo-variations/ns/1.0/"
XMP_NS = "adobe:ns:meta/"
MAX_RECORD = 4096


@dataclass(frozen=True)
class Chunk:
    kind: bytes | int
    payload: bytes
    raw: bytes


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_record(record: object) -> dict:
    if not isinstance(record, dict) or set(record) != {"schema_version", "workflow", "creator", "credit"}:
        raise ValueError("Invalid embedded credit record")
    workflow, creator = record.get("workflow"), record.get("creator")
    if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise ValueError("Unsupported credit schema_version")
    if not isinstance(workflow, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,127}", workflow):
        raise ValueError("Invalid workflow ID")
    if (not isinstance(creator, str) or not creator or len(creator) > 200
            or creator != creator.strip() or any(ord(c) < 32 for c in creator)):
        raise ValueError("Registry creator must be a nonempty name without control characters")
    if record["credit"] != creator + "×变奏":
        raise ValueError("Embedded credit does not match creator")
    return record


def registry_record(registry: Path, workflow: str) -> dict:
    data = json.loads(registry.read_text(encoding="utf-8-sig"))
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1 or not isinstance(data.get("workflows"), dict)):
        raise ValueError("Registry requires schema_version=1 and a workflows object")
    entry = data["workflows"].get(workflow)
    if not isinstance(entry, dict) or not isinstance(entry.get("creator"), str):
        raise ValueError("Workflow has no registered creator")
    creator = entry["creator"]
    return validate_record({"schema_version": 1, "workflow": workflow,
                            "creator": creator, "credit": creator + "×变奏"})


def record_bytes(record: dict) -> bytes:
    data = json.dumps(validate_record(record), ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_RECORD:
        raise ValueError("Credit record is too large")
    return data


def decode_record(data: bytes) -> dict:
    if len(data) > MAX_RECORD:
        raise ValueError("Embedded credit record is too large")
    return validate_record(json.loads(data.decode("utf-8")))


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def png_chunks(data: bytes) -> list[Chunk]:
    if not data.startswith(PNG_MAGIC):
        raise ValueError("Invalid PNG signature")
    chunks, pos = [], 8
    while pos < len(data):
        if pos + 12 > len(data):
            raise ValueError("Truncated PNG chunk")
        size = struct.unpack_from(">I", data, pos)[0]
        end = pos + size + 12
        if end > len(data):
            raise ValueError("Truncated PNG payload")
        kind, payload = data[pos + 4:pos + 8], data[pos + 8:end - 4]
        if zlib.crc32(kind + payload) != struct.unpack_from(">I", data, end - 4)[0]:
            raise ValueError("PNG CRC mismatch")
        chunks.append(Chunk(kind, payload, data[pos:end]))
        pos = end
        if kind == b"IEND":
            if size != 0 or pos != len(data):
                raise ValueError("Invalid PNG IEND or trailing data")
            break
    if (not chunks or chunks[0].kind != b"IHDR" or len(chunks[0].payload) != 13
            or sum(c.kind == b"IHDR" for c in chunks) != 1
            or chunks[-1].kind != b"IEND" or not any(c.kind == b"IDAT" for c in chunks)):
        raise ValueError("Incomplete PNG structure")
    return chunks


def png_credit(chunk: Chunk) -> dict | None:
    if chunk.kind not in {b"iTXt", b"tEXt", b"zTXt"}:
        return None
    parts = chunk.payload.split(b"\0", 1)
    if parts[0] != PNG_KEY:
        return None
    if len(parts) != 2:
        raise ValueError("Malformed reserved PNG credit field")
    rest = parts[1]
    if chunk.kind == b"iTXt":
        if len(rest) < 2 or rest[0] not in (0, 1) or rest[1] != 0:
            raise ValueError("Invalid PNG iTXt credit header")
        fields = rest[2:].split(b"\0", 2)
        if len(fields) != 3:
            raise ValueError("Invalid PNG iTXt credit language fields")
        text, compressed = fields[2], rest[0] == 1
    elif chunk.kind == b"zTXt":
        if not rest or rest[0] != 0:
            raise ValueError("Invalid PNG zTXt credit header")
        text, compressed = rest[1:], True
    else:
        text, compressed = rest, False
    if compressed:
        decoder = zlib.decompressobj()
        text = decoder.decompress(text, MAX_RECORD + 1)
        if not decoder.eof or decoder.unconsumed_tail:
            raise ValueError("Invalid or oversized compressed PNG credit")
    return decode_record(text)


def jpeg_chunks(data: bytes) -> list[Chunk]:
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("Invalid JPEG signature")
    chunks, pos, scans = [], 2, 0
    while pos < len(data):
        start = pos
        if data[pos] != 255:
            raise ValueError("Unsupported or damaged JPEG marker layout")
        while pos < len(data) and data[pos] == 255:
            pos += 1
        if pos >= len(data):
            raise ValueError("Truncated JPEG marker")
        marker = data[pos]
        pos += 1
        if marker == 0xD9:
            chunks.append(Chunk(marker, b"", data[start:]))
            if not scans:
                raise ValueError("JPEG has no scan")
            return chunks
        if marker in (0x00, 0xD8):
            raise ValueError("Unexpected JPEG marker")
        if marker == 1 or 0xD0 <= marker <= 0xD7:
            chunks.append(Chunk(marker, b"", data[start:pos]))
            continue
        if pos + 2 > len(data):
            raise ValueError("Truncated JPEG segment")
        size = struct.unpack_from(">H", data, pos)[0]
        end = pos + size
        if size < 2 or end > len(data):
            raise ValueError("Invalid JPEG segment size")
        payload = data[pos + 2:end]
        pos = end
        if marker == 0xDA:
            scans += 1
            while pos < len(data):
                at = data.find(b"\xff", pos)
                if at < 0:
                    raise ValueError("JPEG scan has no end marker")
                next_byte = at + 1
                while next_byte < len(data) and data[next_byte] == 255:
                    next_byte += 1
                if next_byte >= len(data):
                    raise ValueError("Truncated JPEG scan marker")
                code = data[next_byte]
                if code == 0 or 0xD0 <= code <= 0xD7:
                    pos = next_byte + 1
                else:
                    pos = at
                    break
        chunks.append(Chunk(marker, payload, data[start:pos]))
    raise ValueError("JPEG has no EOI")


def jpeg_credit(chunk: Chunk) -> dict | None:
    return decode_record(chunk.payload[len(JPEG_PREFIX):]) if (
        chunk.kind == 0xFE and chunk.payload.startswith(JPEG_PREFIX)) else None


def riff_chunk(kind: bytes, payload: bytes) -> bytes:
    return kind + struct.pack("<I", len(payload)) + payload + (b"\0" if len(payload) % 2 else b"")


def webp_chunks(data: bytes) -> list[Chunk]:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("Invalid WebP signature")
    if struct.unpack_from("<I", data, 4)[0] + 8 != len(data):
        raise ValueError("WebP RIFF length mismatch or trailing data")
    chunks, pos = [], 12
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("Truncated WebP chunk")
        size = struct.unpack_from("<I", data, pos + 4)[0]
        end = pos + 8 + size + (size % 2)
        if end > len(data) or (size % 2 and data[end - 1] != 0):
            raise ValueError("Invalid WebP payload or padding")
        chunks.append(Chunk(data[pos:pos + 4], data[pos + 8:pos + 8 + size], data[pos:end]))
        pos = end
    if not any(c.kind in {b"VP8 ", b"VP8L", b"ANMF"} for c in chunks):
        raise ValueError("WebP has no image chunk")
    if sum(c.kind == b"XMP " for c in chunks) > 1 or sum(c.kind == b"VP8X" for c in chunks) > 1:
        raise ValueError("Multiple WebP XMP or VP8X chunks are unsupported")
    for i, chunk in enumerate(chunks):
        if chunk.kind == b"VP8X" and (i != 0 or len(chunk.payload) != 10):
            raise ValueError("Invalid WebP VP8X header")
    return chunks


def parse_xmp(packet: bytes) -> ET.Element:
    if re.search(br"<!\s*(DOCTYPE|ENTITY)\b", packet, re.I):
        raise ValueError("XMP DTD/entity declarations are unsupported")
    try:
        text = packet.decode("utf-8")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as exc:
        raise ValueError("XMP must be safe, well-formed UTF-8 XML") from exc
    if len(list(root.iter("{" + RDF_NS + "}RDF"))) != 1:
        raise ValueError("XMP must contain exactly one RDF graph")
    if any(node.tag == "{http://www.w3.org/2000/09/xmldsig#}Signature" for node in root.iter()):
        raise ValueError("Signed XMP cannot safely be modified")
    return root


def xmp_records(root: ET.Element) -> list[dict]:
    records = []
    for desc in root.iter("{" + RDF_NS + "}Description"):
        nodes = [n for n in desc if n.tag == "{" + PV_NS + "}Record"]
        if not nodes:
            continue
        if len(nodes) != 1 or nodes[0].text is None:
            raise ValueError("Malformed XMP credit field")
        record = decode_record(nodes[0].text.encode("utf-8"))
        for tag, key in (("Workflow", "workflow"), ("Creator", "creator"), ("Credit", "credit")):
            matches = [n for n in desc if n.tag == "{" + PV_NS + "}" + tag]
            if len(matches) != 1 or matches[0].text != record[key]:
                raise ValueError("XMP credit fields disagree")
        records.append(record)
    return records


def xmp_semantics(packet: bytes) -> str:
    root = parse_xmp(packet)
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "{" + RDF_NS + "}Description" and any(
                    n.tag == "{" + PV_NS + "}Record" for n in child):
                # Our description has no third-party fields; refuse ambiguity.
                if any(not str(n.tag).startswith("{" + PV_NS + "}") for n in child):
                    raise ValueError("Mixed third-party fields in reserved XMP description")
                parent.remove(child)
    return ET.canonicalize(ET.tostring(root, encoding="unicode"), rewrite_prefixes=True)


def add_xmp(packet: bytes | None, record: dict) -> bytes:
    fields = "".join(f"<pv:{tag}>{escape(record[key])}</pv:{tag}>" for tag, key in
                     (("Workflow", "workflow"), ("Creator", "creator"), ("Credit", "credit")))
    block = (f'<rdf:Description xmlns:rdf="{RDF_NS}" xmlns:pv="{PV_NS}" rdf:about="">'
             + fields + "<pv:Record>" + escape(record_bytes(record).decode("utf-8"))
             + "</pv:Record></rdf:Description>").encode("utf-8")
    if packet is None:
        return (f'<x:xmpmeta xmlns:x="{XMP_NS}"><rdf:RDF xmlns:rdf="{RDF_NS}">'.encode()
                + block + b"</rdf:RDF></x:xmpmeta>")
    parse_xmp(packet)
    positions = []
    parser = expat.ParserCreate(namespace_separator="}")
    parser.StartElementHandler = lambda name, attrs: positions.append([parser.CurrentByteIndex, None]) if name == RDF_NS + "}RDF" else None
    parser.EndElementHandler = lambda name: positions[-1].__setitem__(1, parser.CurrentByteIndex) if name == RDF_NS + "}RDF" else None
    parser.Parse(packet, True)
    start, end = positions[0]
    if packet[end:end + 2] == b"</":
        result = packet[:end] + block + packet[end:]
    else:
        tag = packet[start:end]
        name = re.match(br"<([^\s/>]+)", tag)
        if not name or not tag.endswith(b"/>"):
            raise ValueError("Unsupported XMP RDF insertion point")
        result = packet[:end - 2] + b">" + block + b"</" + name[1] + b">" + packet[end:]
    parse_xmp(result)
    if xmp_semantics(packet) != xmp_semantics(result):
        raise ValueError("Existing XMP semantics changed")
    return result


def simple_webp_header(chunks: list[Chunk]) -> bytes:
    images = [c for c in chunks if c.kind in {b"VP8 ", b"VP8L"}]
    if len(images) != 1 or any(c.kind in {b"ANIM", b"ANMF"} for c in chunks):
        raise ValueError("WebP requires a valid VP8X header for animation")
    image = images[0]
    if image.kind == b"VP8L":
        if len(image.payload) < 5 or image.payload[0] != 0x2F:
            raise ValueError("Invalid WebP lossless header")
        bits = int.from_bytes(image.payload[1:5], "little")
        if bits >> 29:
            raise ValueError("Unsupported WebP lossless version")
        width, height, alpha = (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1, bool(bits & (1 << 28))
    else:
        if len(image.payload) < 10 or image.payload[3:6] != b"\x9d\x01\x2a" or image.payload[0] & 1:
            raise ValueError("Invalid WebP lossy key frame")
        width, height = (struct.unpack_from("<H", image.payload, p)[0] & 0x3FFF for p in (6, 8))
        alpha = any(c.kind == b"ALPH" for c in chunks)
    if not width or not height:
        raise ValueError("Invalid WebP dimensions")
    flags = 4 | (16 if alpha else 0) | (32 if any(c.kind == b"ICCP" for c in chunks) else 0) | (8 if any(c.kind == b"EXIF" for c in chunks) else 0)
    return bytes([flags, 0, 0, 0]) + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")


def inspect(data: bytes) -> tuple[str, list[Chunk], list[dict]]:
    if data.startswith(PNG_MAGIC):
        kind, chunks = "png", png_chunks(data)
        records = [r for c in chunks if (r := png_credit(c)) is not None]
    elif data.startswith(b"\xff\xd8"):
        kind, chunks = "jpeg", jpeg_chunks(data)
        records = [r for c in chunks if (r := jpeg_credit(c)) is not None]
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        kind, chunks = "webp", webp_chunks(data)
        records = [r for c in chunks if c.kind == b"XMP " for r in xmp_records(parse_xmp(c.payload))]
    else:
        raise ValueError("Supported formats are PNG, JPEG and WebP")
    if len(records) > 1:
        raise ValueError("Duplicate embedded credits require manual review")
    return kind, chunks, records


def lossless_metrics(before: bytes, after: bytes) -> dict:
    kind, old, _ = inspect(before)
    new_kind, new, _ = inspect(after)
    if kind != new_kind:
        raise ValueError("Image format changed")
    if kind == "png":
        original_equal = (PNG_MAGIC + b"".join(c.raw for c in old if png_credit(c) is None)
                          == PNG_MAGIC + b"".join(c.raw for c in new if png_credit(c) is None))
        image_before = b"".join(c.raw for c in old if c.kind == b"IDAT")
        image_after = b"".join(c.raw for c in new if c.kind == b"IDAT")
        metric = "png_idat_chunks"
    elif kind == "jpeg":
        original_equal = (b"".join(c.raw for c in old if jpeg_credit(c) is None)
                          == b"".join(c.raw for c in new if jpeg_credit(c) is None))
        image_before = b"".join(c.raw for c in old if c.kind == 0xDA)
        image_after = b"".join(c.raw for c in new if c.kind == 0xDA)
        metric = "jpeg_scan_segments"
    else:
        original_equal = ([c.raw for c in old if c.kind not in {b"XMP ", b"VP8X"}]
                          == [c.raw for c in new if c.kind not in {b"XMP ", b"VP8X"}])
        old_header = next((c.payload for c in old if c.kind == b"VP8X"), None)
        new_header = next((c.payload for c in new if c.kind == b"VP8X"), None)
        expected_header = bytes([old_header[0] | 4]) + old_header[1:] if old_header else simple_webp_header(old)
        original_equal = original_equal and new_header == expected_header
        old_xmp = next((c.payload for c in old if c.kind == b"XMP "), None)
        new_xmp = next((c.payload for c in new if c.kind == b"XMP "), None)
        if new_xmp is None:
            raise ValueError("WebP credit XMP is missing")
        if old_xmp is not None:
            original_equal = original_equal and xmp_semantics(old_xmp) == xmp_semantics(new_xmp)
        else:
            empty = f'<x:xmpmeta xmlns:x="{XMP_NS}"><rdf:RDF xmlns:rdf="{RDF_NS}"/></x:xmpmeta>'.encode()
            original_equal = original_equal and xmp_semantics(new_xmp) == xmp_semantics(empty)
        image_types = {b"VP8 ", b"VP8L", b"ALPH", b"ANIM", b"ANMF"}
        image_before = b"".join(c.raw for c in old if c.kind in image_types)
        image_after = b"".join(c.raw for c in new if c.kind in image_types)
        metric = "webp_image_chunks"
    same_image = image_before == image_after
    if not original_equal or not same_image:
        raise ValueError("Lossless/original-metadata verification failed")
    return {"encoded_image_metric": metric, "encoded_image_sha256_before": digest(image_before),
            "encoded_image_sha256_after": digest(image_after), "encoded_image_bytes_equal": same_image,
            "original_metadata_preserved": original_equal,
            "metadata_preservation": "xmp_fields_semantic_other_chunks_byte_exact" if kind == "webp" else "original_chunks_byte_exact",
            "decoded_pixels_checked": False}


def credited_bytes(data: bytes, record: dict) -> tuple[bytes, bool, dict]:
    record = validate_record(record)
    kind, chunks, records = inspect(data)
    if records:
        if records[0] != record:
            raise ValueError("Existing credit conflicts with requested workflow or registry creator")
        after, changed = data, False
    elif kind == "png":
        payload = PNG_KEY + b"\0\0\0\0\0" + record_bytes(record)
        # Put credit before the first IDAT so metadata-only readers see it
        # without having to decode pixels or consume the image stream.
        pieces, inserted = [PNG_MAGIC], False
        for chunk in chunks:
            if chunk.kind == b"IDAT" and not inserted:
                pieces.append(png_chunk(b"iTXt", payload))
                inserted = True
            pieces.append(chunk.raw)
        after = b"".join(pieces)
        changed = True
    elif kind == "jpeg":
        payload = JPEG_PREFIX + record_bytes(record)
        comment = b"\xff\xfe" + struct.pack(">H", len(payload) + 2) + payload
        inserted, segments = False, [b"\xff\xd8"]
        for chunk in chunks:
            if chunk.kind == 0xDA and not inserted:
                segments.append(comment)
                inserted = True
            segments.append(chunk.raw)
        after, changed = b"".join(segments), True
    else:
        packet = next((c.payload for c in chunks if c.kind == b"XMP "), None)
        new_xmp = riff_chunk(b"XMP ", add_xmp(packet, record))
        pieces = []
        if not any(c.kind == b"VP8X" for c in chunks):
            pieces.append(riff_chunk(b"VP8X", simple_webp_header(chunks)))
        for chunk in chunks:
            if chunk.kind == b"VP8X":
                pieces.append(riff_chunk(b"VP8X", bytes([chunk.payload[0] | 4]) + chunk.payload[1:]))
            elif chunk.kind == b"XMP ":
                pieces.append(new_xmp)
            else:
                pieces.append(chunk.raw)
        if packet is None:
            pieces.append(new_xmp)
        body = b"WEBP" + b"".join(pieces)
        after, changed = b"RIFF" + struct.pack("<I", len(body)) + body, True
    if inspect(after)[2] != [record]:
        raise ValueError("Embedded credit read-back failed")
    return after, changed, lossless_metrics(data, after)


def main() -> int:
    # Machine-readable JSON stays UTF-8 on Windows, including redirected output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("write", "read", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("--input", type=Path, required=True)
        if name != "read":
            sub.add_argument("--workflow", required=True)
            sub.add_argument("--registry", type=Path, required=True)
        if name == "write":
            sub.add_argument("--output", type=Path, required=True,
                             help="New output only; input and existing files are never overwritten")
        if name == "verify":
            sub.add_argument("--against", type=Path, help="Optional pre-credit file for byte/metadata invariant verification")
    args = parser.parse_args()
    try:
        data = args.input.read_bytes()
        kind, _, records = inspect(data)
        if args.command == "read":
            result = {"status": "read", "format": kind, "credit_found": bool(records),
                      "credit_count": len(records), "metadata": records[0] if records else None}
        else:
            expected = registry_record(args.registry, args.workflow)
            if args.command == "verify":
                if records != [expected]:
                    raise ValueError("Embedded credit does not match workflow/registry")
                result = {"status": "verified", "format": kind, **expected,
                          "credit_count": 1, "metadata_verified": True}
                if args.against:
                    result.update(lossless_metrics(args.against.read_bytes(), data))
            else:
                if args.input.resolve() == args.output.resolve():
                    raise ValueError("Input and output must be different files")
                if args.output.exists():
                    raise ValueError("Output already exists; choose a new output file")
                suffixes = {"png": {".png"}, "jpeg": {".jpg", ".jpeg"}, "webp": {".webp"}}
                if args.output.suffix.lower() not in suffixes[kind]:
                    raise ValueError("Output extension does not match input image format")
                after, changed, metrics = credited_bytes(data, expected)
                with args.output.open("xb") as handle:
                    handle.write(after)
                actual = args.output.read_bytes()
                if inspect(actual)[2] != [expected] or actual != after or args.input.read_bytes() != data:
                    raise ValueError("On-disk verification or source integrity check failed")
                result = {"status": "written" if changed else "already_credited_copy",
                          "format": kind, **expected, "credit_count": 1, "metadata_verified": True,
                          "input_file_sha256": digest(data), "output_file_sha256": digest(actual),
                          "source_file_unchanged": True, **metrics}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, UnicodeError, struct.error, zlib.error, expat.ExpatError) as exc:
        # No filenames, user paths, times, EXIF identities or GPS are included.
        message = str(exc) if not isinstance(exc, json.JSONDecodeError) else "Invalid JSON registry or credit record"
        print(json.dumps({"status": "error", "message": message}, ensure_ascii=False), file=sys.stderr)
    except OSError as exc:
        print(json.dumps({"status": "error", "message": "File operation failed", "errno": exc.errno}), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
