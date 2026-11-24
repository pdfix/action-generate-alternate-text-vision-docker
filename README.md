# Generate Alternate Text Vision

Runs locally and uses AI Vision models to describe image content in alternative text. For PDF output without watermarks, a **PDFix SDK** license is required.

> [!WARNING]
> **Deprecated.** This action is no longer developed and no new Docker image is published (the last one is
> `pdfix/generate-alternate-text-vision:v1.0.2`). For new work use the local alternate text generator
> [Generate Alternate Text BLIP](https://github.com/pdfix/action-generate-alternate-text-blip-large-docker),
> which writes better descriptions, especially of charts, logos and composite figures.
>
> The repository stays available for users who installed the Vision action in PDFix Desktop earlier: you can
> see how it works, build an updated image yourself (see [Building the image](#building-the-image)) or use it as
> a base for your own action.

## Table of Contents

- [Generate Alternate Text Vision](#generate-alternate-text-vision)
  - [Getting started](#getting-started)
  - [Building the image](#building-the-image)
  - [Usage](#usage)
  - [Commands](#commands)
  - [Arguments](#arguments)
  - [Params JSON](#params-json)
  - [Examples](#examples)
  - [Model](#model)
  - [Help \& support](#help--support)
  - [Licenses](#licenses)

## Getting started

You need Docker installed. The first run downloads the image and may take longer than later runs.

## Building the image

The model is not stored in the repository. Download it and build the image:

```bash
python3 download_models.py
mkdir -p model
cp models/models--nlpconnect--vit-gpt2-image-captioning/snapshots/*/* model/
# the same weights are in model.safetensors, the copy only makes the image larger
rm model/pytorch_model.bin
docker build -t pdfix/generate-alternate-text-vision:latest .
```

To use your image in PDFix Desktop, export its configuration with the `config` command and add the action to
PDFix Desktop.

## Usage

Mount a folder into the container and run a subcommand:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/generate-alternate-text-vision:latest <command> [options]
```

## Commands

- `generate-alt-text`: Generate alternate text (PDF → PDF or supported image → TXT)

## Arguments

### `generate-alt-text`

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--input`, `-i` | yes | Path to an existing `.pdf` or supported image file | Input PDF or image |
| `--output`, `-o` | yes | Path for output `.pdf` or `.txt` (must match mode) | Output file |
| `--model` | no | Path to model directory inside the container (default: `model`); must not contain `..` | Local Vision model path |
| `--params` | for PDF → PDF | Path to a `.json` file | Tag filter parameters (see [Params JSON](#params-json)) |
| `--overwrite` | no | Boolean string: `true`/`false`, `yes`/`no`, `1`/`0` (default: `false`) | Overwrite existing Alt text |
| `--zoom` | no | Float (default **2.0**) | Page render zoom for PDF mode |
| `--name` | no | String (PDFix account license name) | PDFix license name |
| `--key` | no | String (PDFix account license key) | PDFix license key |

Default tag filter when `--params` is omitted: `Figure`.

## Params JSON

`--params` points to a JSON array of parameter objects. Each object has at least `name` and `value`; the CLI reads those fields to decide which tags to process (PDF → PDF only).

### `tag_names`

`tag_names` is an ECMAScript regular expression matching tag names, or a template `tag_update` object.

Example (`example/params_alt_text.json`) — match `Figure` tags:

```json
[
    {
        "title": "Tags",
        "desc": "Specify the tags using a ECMAScript regular expression or define them by template tag_update",
        "name": "tag_names",
        "type": "tag",
        "value": "Figure",
        "values": [
            {
                "desc": "All tags",
                "value": ".*"
            }
        ]
    }
]
```

Use `"value": ".*"` to match all tags.

## Examples

Generate alternate text for figures in a PDF:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/generate-alternate-text-vision:latest \
  generate-alt-text --name "${LICENSE_NAME}" --key "${LICENSE_KEY}" \
  -i /data/input.pdf -o /data/output.pdf --model /model \
  --params /data/example/params_alt_text.json
```

Caption a single image to a TXT file:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/generate-alternate-text-vision:latest \
  generate-alt-text -i /data/image.jpg -o /data/output.txt --model /model
```

## Model

The image bundles Vision captioning models and runs offline. Point `--model` at the directory inside the image that contains the bundled weights (often `/model`).

## Help & support

For PDFix SDK licensing or issues, contact `support@pdfix.net`.

## Licenses

- [PDFix Terms](https://pdfix.net/terms)
- Vision captioning model ([vit-gpt2-image-captioning](https://huggingface.co/nlpconnect/vit-gpt2-image-captioning)) — [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)

