import argparse
import json
import logging
import re
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from constants import CONFIG_FILE, IMAGE_FILE_EXT_REGEX, SUPPORTED_IMAGE_EXT
from exceptions import (
    EC_ARG_GENERAL,
    MESSAGE_ARG_GENERAL,
    ArgumentException,
    ArgumentInputNotImageException,
    ArgumentInputNotPdfException,
    ArgumentOutputExtensionException,
    ArgumentOutputFolderNotExistsException,
    ArgumentZoomException,
    ExpectedException,
    InvalidRegexOrTemplateException,
)
from image_update import DockerImageContainerUpdateChecker
from logger import get_logger
from params_parser import ParamsParser
from process_image import generate_alt_text_into_txt
from process_pdf import GenerateAltTextsInPdf

logger: logging.Logger = get_logger("app_logger")

DEFAULT_TAGS: str = "Figure"


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
            case "params":
                parser.add_argument(
                    "--params",
                    type=str,
                    required=False,
                    help="Path to JSON file with tag filter parameters (required for PDF → PDF).",
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


def check_output_file(output_path: str) -> str:
    """
    Check the output file extension and that its folder exists before any processing.

    Args:
        output_path (str): Path to the output PDF or TXT file.

    Returns:
        Output extension, ".pdf" or ".txt", which selects the mode.
    """
    extension: str = Path(output_path).suffix.lower()
    if extension not in (".pdf", ".txt"):
        raise ArgumentOutputExtensionException()

    output_folder: Path = Path(output_path).resolve().parent
    if not output_folder.is_dir():
        raise ArgumentOutputFolderNotExistsException(output_folder.as_posix())

    return extension


def check_input_file(input_path: str, output_extension: str) -> None:
    """
    Check that the input is an existing file of the type the mode needs.

    Args:
        input_path (str): Path to the input PDF or image.
        output_extension (str): ".pdf" for PDF to PDF, ".txt" for image to TXT.
    """
    path: Path = Path(input_path)
    if output_extension == ".pdf":
        if path.suffix.lower() != ".pdf" or not path.is_file():
            raise ArgumentInputNotPdfException(input_path)
    elif not re.search(IMAGE_FILE_EXT_REGEX, input_path, re.IGNORECASE) or not path.is_file():
        raise ArgumentInputNotImageException(input_path)


def check_zoom(zoom: float) -> None:
    """
    Check the rendering zoom level.

    Args:
        zoom (float): Zoom level for rendering the page.
    """
    if zoom < 1.0 or zoom > 4.0:
        raise ArgumentZoomException()


def resolve_regex_template(params_path: Optional[str]) -> str | Path | dict:
    """
    Resolve tag filter from --params (regex or template) or the default Figure regex.

    Args:
        params_path (Optional[str]): Path to params JSON, or None.

    Returns:
        Either a regex string or a template dict.
    """
    if not params_path:
        return DEFAULT_TAGS

    params_parser = ParamsParser(params_path)
    params_parser.parse()
    tag_names: Any = params_parser.get("tag_names")
    if isinstance(tag_names, str):
        return tag_names
    if isinstance(tag_names, dict):
        return tag_names
    raise InvalidRegexOrTemplateException()


def run_generate_alt_text_subcommand(args) -> None:
    output_extension: str = check_output_file(args.output)
    check_input_file(args.input, output_extension)
    check_zoom(args.zoom)

    if output_extension == ".txt":
        generate_alt_text_into_txt(args.input, args.output, args.model)
        return

    tag_filter: str | Path | dict = resolve_regex_template(getattr(args, "params", None))
    if isinstance(tag_filter, dict):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as template_file:
            with open(template_file.name, "w", encoding="utf-8") as template_file_write:
                json.dump(tag_filter, template_file_write)
            generate_alt_text_in_pdf(args, Path(template_file.name))
    else:
        generate_alt_text_in_pdf(args, tag_filter)


def generate_alt_text_in_pdf(args, regex_template: str | Path) -> None:
    """
    Generate alternate texts for selected tags in PDF document.

    Args:
        args: Parsed command line arguments.
        regex_template (str | Path): Regex or path to template JSON for matching tags.
    """
    processor: GenerateAltTextsInPdf = GenerateAltTextsInPdf(
        args.input, args.output, args.name, args.key, args.overwrite, args.zoom, args.model, regex_template
    )
    processor.generate_alt_texts_in_pdf()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a PDF file with Vision to generate alt text",
    )

    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

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
        ["name", "key", "input", "output", "overwrite", "zoom", "model", "params"],
        True,
        "The output PDF or TXT file",
    )
    generate_alt_text_subparser.set_defaults(func=run_generate_alt_text_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except ExpectedException as e:
        logger.error(e.message)
        sys.exit(e.error_code)
    except SystemExit as e:
        if e.code != 0:
            logger.error(MESSAGE_ARG_GENERAL)
            sys.exit(EC_ARG_GENERAL)
        # This happens when --help is used, exit gracefully
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to run the program:")
        logger.exception(e)
        sys.exit(1)

    if hasattr(args, "func"):
        # Check for updates only when help is not checked
        update_checker = DockerImageContainerUpdateChecker()
        # Check it in separate thread not to be delayed when there is slow or no internet connection
        update_thread = threading.Thread(target=update_checker.check_for_image_updates)
        update_thread.start()

        # Measure the time it takes to process the input
        start_time: float = time.time()
        current_time: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.info(f"Processing started at: {current_time}")

        # Run subcommand
        try:
            args.func(args)
        except ExpectedException as e:
            logger.error(e.message)
            if e.sdk_error:
                logger.error(e.sdk_error)
            sys.exit(e.error_code)
        except Exception as e:
            # not expected exception -> print stack trace and what exception happened
            logger.error("Failed to run the program:")
            logger.exception(e)
            sys.exit(1)
        finally:
            elapsed_time: float = time.time() - start_time
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            logger.info(f"Processing finished at: {current_time}. Elapsed time: {elapsed_time:.2f} seconds")

            # Make sure to let update thread finish before exiting
            update_thread.join()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
