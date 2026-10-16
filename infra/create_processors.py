#!/usr/bin/env python3
"""Create the Document AI processors Kredibel uses (docs/16 §3; spec 022 phase B).

Creates an OCR processor (Enterprise Document OCR) in DOCAI_LOCATION, or reuses the one with the
same display name, and prints its ID and the stable version name to put in
DOCAI_OCR_PROCESSOR_ID and DOCAI_OCR_VERSION. With --form or --invoice it does the same for
those processors (P1).

Usage (from the repository root, with Application Default Credentials):
  uv run --project backend python infra/create_processors.py --project "$PROJECT_ID"
"""

import argparse
import sys

from google.api_core.client_options import ClientOptions
from google.cloud import documentai


def ensure(
    client: documentai.DocumentProcessorServiceClient, parent: str, kind: str, name: str
) -> documentai.Processor:
    for processor in client.list_processors(parent=parent):
        if processor.display_name == name:
            return processor
    return client.create_processor(
        parent=parent, processor=documentai.Processor(type_=kind, display_name=name)
    )


def stable_version(processor: documentai.Processor) -> str:
    """The processor's default version: a pretrained, stable model, pinned by name in settings."""
    return processor.default_processor_version.split("/")[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="us")
    parser.add_argument("--form", action="store_true")
    parser.add_argument("--invoice", action="store_true")
    args = parser.parse_args()
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint=f"{args.location}-documentai.googleapis.com")
    )
    parent = client.common_location_path(args.project, args.location)
    wanted = [("OCR_PROCESSOR", "kredibel-ocr", "DOCAI_OCR")]
    if args.form:
        wanted.append(("FORM_PARSER_PROCESSOR", "kredibel-form", "DOCAI_FORM"))
    if args.invoice:
        wanted.append(("INVOICE_PROCESSOR", "kredibel-invoice", "DOCAI_INVOICE"))
    for kind, name, prefix in wanted:
        processor = ensure(client, parent, kind, name)
        print(f"{prefix}_PROCESSOR_ID={processor.name.split('/')[-1]}")
        print(f"{prefix}_VERSION={stable_version(processor)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
