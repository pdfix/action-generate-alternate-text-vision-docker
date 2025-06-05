from transformers import AutoTokenizer, VisionEncoderDecoderModel, ViTImageProcessor

cache_dir = "./models"

model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning", cache_dir=cache_dir)
feature_extractor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning", cache_dir=cache_dir)
tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning", cache_dir=cache_dir)

# now model data is downloaded in "./models/models--nlpconnect--vit-gpt2-image-captioning/snapshots/<hash>/"
