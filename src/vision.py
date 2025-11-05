from typing import Any

import torch
from PIL import Image
from transformers import AutoTokenizer, BatchFeature, VisionEncoderDecoderModel, ViTImageProcessor


def generate_alt_text_description(image_path: str, model_path: str) -> list[str]:
    """
    Generate alt text description using vission AI.

    Args:
        image_path (str): Path to file containing image.
        model_path (str): Path to Vision model. Default value is "model".

    Returns:
        List of possible texts.
    """
    model: Any = VisionEncoderDecoderModel.from_pretrained(model_path, local_files_only=True)
    feature_extractor: ViTImageProcessor = ViTImageProcessor.from_pretrained(model_path, local_files_only=True)
    tokenizer: Any = AutoTokenizer.from_pretrained(model_path, local_files_only=True)

    # Select device and assign it
    device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Generating settings
    max_length: int = 16
    num_beams: int = 1  # otherwise _reorder_cache() needs to be implemented
    gen_kwargs: dict[str, int] = {"max_length": max_length, "num_beams": num_beams}

    # Load image data
    image: Image.Image = Image.open(image_path)
    if image.mode != "RGB":
        image = image.convert(mode="RGB")

    pixel_values: BatchFeature = feature_extractor(images=image, return_tensors="pt").pixel_values
    pixel_values = pixel_values.to(device)

    # Generate alt texts
    output_ids: Any = model.generate(pixel_values, **gen_kwargs)
    preds: Any = tokenizer.batch_decode(output_ids, skip_special_tokens=True)

    # Return alt texts
    return [str(pred).strip() for pred in preds]
