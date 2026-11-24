import logging

from tqdm import tqdm

from logger import get_logger
from vision import VisionCaptioner

logger: logging.Logger = get_logger("app_logger")


def generate_alt_text_into_txt(input_path: str, output_path: str, model_path: str) -> None:
    """
    For input image file run Vision to generate alt text and save it to output file.

    Args:
        input_path (str): Input path to the image file.
        output_path (str): Output path for saving the TXT file.
        model_path (str): Path to Vision model. Default value is "model".
    """
    with tqdm(total=100) as progress_bar:
        progress_bar.set_description("Processing")

        alt_text: str = VisionCaptioner(model_path).describe(input_path)
        logger.info(f"Alternate text: '{alt_text}'")

        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(alt_text)

        progress_bar.n = 100
        progress_bar.set_description("Done")
        progress_bar.refresh()
