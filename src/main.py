import argparse
import os
import re
import sys
import threading
import traceback
from pathlib import Path

from constants import IMAGE_FILE_EXT_REGEX, SUPPORTED_IMAGE_EXT
from image_update import DockerImageContainerUpdateChecker
from process_image import generate_alt_text_into_txt
from process_pdf import generate_alt_texts_in_pdf


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
                parser.add_argument("--key", type=str, help="PDFix license key")
            case "name":
                parser.add_argument("--name", type=str, help="PDFix license name")
            case "output":
                parser.add_argument("--output", "-o", type=str, required=required_output, help=output_help)
            case "overwrite":
                parser.add_argument(
                    "--overwrite",
                    action="store_true",
                    required=False,
                    default=False,
                    help="Overwrite alternate text if already present in the tag",
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
    config_path = os.path.join(Path(__file__).parent.absolute(), "../config.json")

    with open(config_path, "r", encoding="utf-8") as file:
        if path is None:
            print(file.read())
        else:
            with open(path, "w") as out:
                out.write(file.read())


def run_generate_alt_text_subcommand(args) -> None:
    generate_alt_text(args.input, args.output, args.name, args.key, args.overwrite)


def generate_alt_text(input_file: str, output_file: str, license_name: str, license_key: str, overwrite: bool) -> None:
    """
    Run image detect and use vission to generate alternate text description for images.

    Args:
        input_file (str): Path to PDF or image.
        output_file (str): Path to PDF or TXT.
        license_name (str): Name used in authorization in PDFix-SDK.
        license_key (str): Key used in authorization in PDFix-SDK.
        overwrite (bool): Overwrite alternate text if already present.
    """
    if not os.path.isfile(input_file):
        raise Exception(f"Error: The input file '{input_file}' does not exist.")

    if input_file.lower().endswith(".pdf") and output_file.lower().endswith(".pdf"):
        generate_alt_texts_in_pdf(input_file, output_file, license_name, license_key, overwrite)
    elif re.search(IMAGE_FILE_EXT_REGEX, input_file, re.IGNORECASE) and output_file.lower().endswith(".txt"):
        generate_alt_text_into_txt(input_file, output_file)
    else:
        raise Exception("No allowed input output file combination. Please see --help.")


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
        generate_alt_text_subparser, ["name", "key", "input", "output", "overwrite"], True, "The output PDF or TXT file"
    )
    generate_alt_text_subparser.set_defaults(func=run_generate_alt_text_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 0:  # This happens when --help is used, exit gracefully
            sys.exit(0)
        print("Failed to parse arguments. Please check the usage and try again.")
        sys.exit(e.code)

    if hasattr(args, "func"):
        # Check for updates only when help is not checked
        update_checker = DockerImageContainerUpdateChecker()
        # Check it in separate thread not to be delayed when there is slow or no internet connection
        update_thread = threading.Thread(target=update_checker.check_for_image_updates)
        update_thread.start()

        # Run subcommand
        try:
            args.func(args)
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
