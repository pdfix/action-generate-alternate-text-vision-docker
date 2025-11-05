import argparse
import os
import re
import sys
import threading
import traceback
from pathlib import Path
from typing import Any

from constants import CONFIG_FILE, IMAGE_FILE_EXT_REGEX, SUPPORTED_IMAGE_EXT
from exceptions import (
    EC_ARG_GENERAL,
    MESSAGE_ARG_GENERAL,
    ArgumentException,
    ArgumentInputMissingException,
    ArgumentInputOutputNotAllowedException,
    ExpectedException,
)
from image_update import DockerImageContainerUpdateChecker
from process_image import generate_alt_text_into_txt
from process_pdf import generate_alt_texts_in_pdf


def str2bool(value: Any) -> bool:
    """
    Helper function to convert argument to boolean.

    Args:
        value (Any): The value to convert to boolean.

    Returns:
        Parsed argument as boolean.
    """
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "1"):
        return True
    elif value.lower() in ("no", "false", "f", "0"):
        return False
    else:
        raise ArgumentException(f"{MESSAGE_ARG_GENERAL} Boolean value expected.")


def set_arguments(
    parser: argparse.ArgumentParser,
    names: list,
    required_output: bool = True,
    output_help: str = "",
) -> None:
    """
    Set arguments for the parser based on the provided names and options.

    Args:
        parser (argparse.ArgumentParser): The argument parser to set arguments for.
        names (list): List of argument names to set.
        required_output (bool): Whether the output argument is required. Defaults to True.
        output_help (str): Help shown for --output argument. Defaults to "".
    """
    for name in names:
        match name:
            case "input":
                parser.add_argument("--input", "-i", type=str, required=True, help="The input PDF file")
            case "key":
                parser.add_argument("--key", type=str, default="", nargs="?", help="PDFix license key")
            case "model":
                parser.add_argument(
                    "--model",
                    type=str,
                    default="model",
                    help='Path to local model directory. It cannot contain "..". Default value is "model".',
                )
            case "name":
                parser.add_argument("--name", type=str, default="", nargs="?", help="PDFix license name")
            case "output":
                parser.add_argument("--output", "-o", type=str, required=required_output, help=output_help)
            case "overwrite":
                parser.add_argument(
                    "--overwrite",
                    type=str2bool,
                    default=False,
                    help="Overwrite alternate text if already present in the tag",
                )
            case "zoom":
                parser.add_argument(
                    "--zoom", type=float, default=2.0, help="Zoom level for the PDF page rendering (default: 2.0)."
                )


def run_config_subcommand(args) -> None:
    get_pdfix_config(args.output)


def get_pdfix_config(path: str) -> None:
    """
    If Path is not provided, output content of config.
    If Path is provided, copy config to destination path.

    Args:
        path (string): Destination path for config.json file
    """
    config_path: Path = Path(__file__).parent.parent.joinpath(CONFIG_FILE).resolve()

    with open(config_path, "r", encoding="utf-8") as file:
        if path is None:
            print(file.read())
        else:
            with open(path, "w") as out:
                out.write(file.read())


def run_generate_alt_text_subcommand(args) -> None:
    generate_alt_text(args.input, args.output, args.name, args.key, args.overwrite, args.zoom, args.model)


def generate_alt_text(
    input_file: str,
    output_file: str,
    license_name: str,
    license_key: str,
    overwrite: bool,
    zoom: float,
    model_path: str,
) -> None:
    """
    Run image detect and use vission to generate alternate text description for images.

    Args:
        input_file (str): Path to PDF or image.
        output_file (str): Path to PDF or TXT.
        license_name (str): Name used in authorization in PDFix-SDK.
        license_key (str): Key used in authorization in PDFix-SDK.
        overwrite (bool): Overwrite alternate text if already present.
        zoom (float): Zoom level for rendering the page.
        model_path (str): Path to Vision model. Default value is "model".
    """
    if not os.path.isfile(input_file):
        raise ArgumentInputMissingException(input_file)

    if input_file.lower().endswith(".pdf") and output_file.lower().endswith(".pdf"):
        generate_alt_texts_in_pdf(input_file, output_file, license_name, license_key, overwrite, zoom, model_path)
    elif re.search(IMAGE_FILE_EXT_REGEX, input_file, re.IGNORECASE) and output_file.lower().endswith(".txt"):
        generate_alt_text_into_txt(input_file, output_file, model_path)
    else:
        raise ArgumentInputOutputNotAllowedException()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a PDF file with Vission to generate alt text",
    )

    subparsers = parser.add_subparsers(dest="subparser")

    # Config subparser
    config_subparser = subparsers.add_parser(
        "config",
        help="Extract config file for integration",
    )
    set_arguments(
        config_subparser,
        ["output"],
        False,
        "Output to save the config JSON file. Application output is used if not provided",
    )
    config_subparser.set_defaults(func=run_config_subcommand)

    # Generate alternate text images subparser
    generate_alt_text_help = "Run alternate text description."
    generate_alt_text_help += " Runs in 2 modes. First mode is PDF -> PDF."
    generate_alt_text_help += " Second mode is image file -> TXT."
    generate_alt_text_help += f" Allowed image types: {SUPPORTED_IMAGE_EXT}"
    generate_alt_text_subparser = subparsers.add_parser("generate-alt-text", help=generate_alt_text_help)
    set_arguments(
        generate_alt_text_subparser,
        ["name", "key", "input", "output", "overwrite", "zoom", "model"],
        True,
        "The output PDF or TXT file",
    )
    generate_alt_text_subparser.set_defaults(func=run_generate_alt_text_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except ExpectedException as e:
        print(e.message, file=sys.stderr)
        sys.exit(e.error_code)
    except SystemExit as e:
        if e.code != 0:
            print(MESSAGE_ARG_GENERAL, file=sys.stderr)
            sys.exit(EC_ARG_GENERAL)
        # This happens when --help is used, exit gracefully
        sys.exit(0)
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print(f"Failed to run the program: {e}", file=sys.stderr)
        sys.exit(1)

    if hasattr(args, "func"):
        # Check for updates only when help is not checked
        update_checker = DockerImageContainerUpdateChecker()
        # Check it in separate thread not to be delayed when there is slow or no internet connection
        update_thread = threading.Thread(target=update_checker.check_for_image_updates)
        update_thread.start()

        # Run subcommand
        try:
            args.func(args)
        except ExpectedException as e:
            print(e.message, file=sys.stderr)
            sys.exit(e.error_code)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"Failed to run the program: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            # Make sure to let update thread finish before exiting
            update_thread.join()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
