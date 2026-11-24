from typing import Any

import torch
from PIL import Image
from transformers import AutoTokenizer, BatchFeature, VisionEncoderDecoderModel, ViTImageProcessor
from transformers.utils import logging as transformers_logging

# Hugging Face libraries log and show their own progress bars when loading the model; keep only ours.
# This also hides the load report of unused weights and the attention mask warning of every caption.
transformers_logging.disable_progress_bar()
transformers_logging.set_verbosity_error()


class VisionCaptioner:
    """
    Vision (ViT + GPT-2 image captioning) model that describes images.
    The model is loaded once and used for all images.
    """

    def __init__(self, model_path: str) -> None:
        """
        Load the model, image processor and tokenizer.

        Args:
            model_path (str): Path to Vision model. Default value is "model".
        """
        self.model: Any = VisionEncoderDecoderModel.from_pretrained(model_path, local_files_only=True)
        self.feature_extractor: ViTImageProcessor = ViTImageProcessor.from_pretrained(model_path, local_files_only=True)
        self.tokenizer: Any = AutoTokenizer.from_pretrained(model_path, local_files_only=True)

        # Select device and assign it
        self.device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def describe(self, image_path: str) -> str:
        """
        Generate alt text description of an image.

        Args:
            image_path (str): Path to file containing image.

        Returns:
            Caption of image.
        """
        # Generating settings
        max_length: int = 16
        num_beams: int = 1  # otherwise _reorder_cache() needs to be implemented
        gen_kwargs: dict[str, int] = {"max_length": max_length, "num_beams": num_beams}

        # Load image data
        image: Image.Image = Image.open(image_path)
        if image.mode != "RGB":
            image = image.convert(mode="RGB")

        pixel_values: BatchFeature = self.feature_extractor(images=image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)

        # Generate alt text
        output_ids: Any = self.model.generate(pixel_values, **gen_kwargs)
        preds: Any = self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)

        # Return alt text
        return str(preds[0]).strip()
