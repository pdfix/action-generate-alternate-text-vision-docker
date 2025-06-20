from vision import generate_alt_text_description


def generate_alt_text_into_txt(input_path: str, output_path: str, model_path: str) -> None:
    """
    For input image file run vission generate alt text and save it to output file.

    Args:
        input_path (str): Input path to the image file.
        output_path (str): Output path for saving the TXT file.
        model_path (str): Path to Vision model. Default value is "model".
    """
    response = generate_alt_text_description(input_path, model_path)
    alt_text_by_vission = response[0]

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(alt_text_by_vission)
