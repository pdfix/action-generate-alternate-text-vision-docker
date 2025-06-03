import torch
from PIL import Image
from transformers import AutoTokenizer, VisionEncoderDecoderModel, ViTImageProcessor


def generate_alt_text_description(image_path: str) -> list[str]:
    """
    Generate alt text description using vission AI.

    Args:
        image_path (str): Path to file containing image.

    Returns:
        List of possible texts.
    """
    # Select models
    model = VisionEncoderDecoderModel.from_pretrained(
        "nlpconnect/vit-gpt2-image-captioning",
    )
    feature_extractor = ViTImageProcessor.from_pretrained(
        "nlpconnect/vit-gpt2-image-captioning",
    )
    tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")

    # Select device and assign it
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Generating settings
    max_length = 16
    num_beams = 4
    gen_kwargs = {"max_length": max_length, "num_beams": num_beams}

    # Load image data
    image: Image.Image = Image.open(image_path)
    if image.mode != "RGB":
        image = image.convert(mode="RGB")

    pixel_values = feature_extractor(images=image, return_tensors="pt").pixel_values
    pixel_values = pixel_values.to(device)

    # Generate alt texts
    output_ids = model.generate(pixel_values, **gen_kwargs)
    preds = tokenizer.batch_decode(output_ids, skip_special_tokens=True)

    # Return alt texts
    return [pred.strip() for pred in preds]
