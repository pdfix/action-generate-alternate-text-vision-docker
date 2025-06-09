import argparse
import os
import sys
import traceback
from pathlib import Path

from image_update import DockerImageContainerUpdateChecker
from process_pdf import detect_image_and_generate_alt_text


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


def run_detect_subcommand(args) -> None:
    input_file = args.input

    if not os.path.isfile(input_file):
        raise Exception(f"Error: The input file '{input_file}' does not exist.")

    output_file = args.output

    if not input_file.lower().endswith(".pdf") or not output_file.lower().endswith(".pdf"):
        raise Exception("Input and output file must be PDF")

    detect(input_file, output_file, args.name, args.key, args.overwrite)


def detect(input_file: str, output_file: str, license_name: str, license_key: str, overwrite: bool) -> None:
    """
    Run image detect and use vission to generate alternate text description for images.

    Args:
        input_file (str): Path to PDF document.
        output_file (str): Path to PDF document.
        license_name (str): Name used in authorization in PDFix-SDK.
        license_key (str): Key used in authorization in PDFix-SDK.
        overwrite (bool): Overwrite alternate text if already present.
    """
    detect_image_and_generate_alt_text(input_file, output_file, license_name, license_key, overwrite)


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

    # Detect subparser
    detect_subparser = subparsers.add_parser(
        "detect",
        help="Run alternate text description",
    )
    set_arguments(detect_subparser, ["name", "key", "input", "output", "overwrite"], True, "The output PDF file")
    detect_subparser.set_defaults(func=run_detect_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 0:  # This happens when --help is used, exit gracefully
            sys.exit(0)
        print("Failed to parse arguments. Please check the usage and try again.")
        sys.exit(e.code)

    # Update of docker image checker
    update_checker = DockerImageContainerUpdateChecker()
    update_checker.check_for_image_updates()

    if hasattr(args, "func"):
        # Run subcommand
        try:
            args.func(args)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"Failed to run the program: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
