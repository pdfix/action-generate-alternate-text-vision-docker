# Generate Alternate Text Vision

Runs locally and uses AI Vision models to describe image content in alternative text. For PDF output without watermarks, a **PDFix SDK** license is required.

## Table of Contents

- [Generate Alternate Text Vision](#generate-alternate-text-vision)
  - [Getting started](#getting-started)
  - [Usage](#usage)
  - [Commands](#commands)
  - [Arguments](#arguments)
  - [Examples](#examples)
  - [Model](#model)
  - [Help \& support](#help--support)
  - [Licenses](#licenses)

## Getting started

You need Docker installed. The first run downloads the image and may take longer than later runs.

## Usage

Mount a folder into the container and run a subcommand:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/alt-text-vision:latest <command> [options]
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
| `--overwrite` | no | Boolean string: `true`/`false`, `yes`/`no`, `1`/`0` (default: `false`) | Overwrite existing Alt text |
| `--zoom` | no | Float (default **2.0**) | Page render zoom for PDF mode |
| `--name` | no | String (PDFix account license name) | PDFix license name |
| `--key` | no | String (PDFix account license key) | PDFix license key |

## Examples

Generate alternate text for figures in a PDF:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/alt-text-vision:latest \
  generate-alt-text --name "${LICENSE_NAME}" --key "${LICENSE_KEY}" \
  -i /data/input.pdf -o /data/output.pdf --model /model
```

Caption a single image to a TXT file:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/alt-text-vision:latest \
  generate-alt-text -i /data/image.jpg -o /data/output.txt --model /model
```

## Model

The image bundles Vision captioning models and runs offline. Point `--model` at the directory inside the image that contains the bundled weights (often `/model`).

## Help & support

For PDFix SDK licensing or issues, contact `support@pdfix.net`.

## Licenses

- [PDFix Terms](https://pdfix.net/terms)
- Vision captioning model ([vit-gpt2-image-captioning](https://huggingface.co/nlpconnect/vit-gpt2-image-captioning)) — [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
