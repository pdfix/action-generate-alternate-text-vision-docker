# Alt Text Generator

A Docker image that automatically generates alt text for all Figures in PDF document.

## Table of Contents

- [Alt Text Generator](#alt-text-generator)
  - [Table of Contents](#table-of-contents)
  - [Getting Started](#getting-started)
  - [Exporting Configuration for Integration](#exporting-configuration-for-integration)
  - [License](#license)
  - [Help \& Support](#help--support)

## Getting Started

To use this Docker application, you'll need to have Docker installed on your system. If Docker is not installed, please follow the instructions on the [official Docker website](https://docs.docker.com/get-docker/) to install it.
First run will pull the docker image, which may take some time. Make your own image for more advanced use.

## Run using Command Line Interface

To run docker container as CLI you should share the folder with PDF to process using `-v` parameter.
In this example all Figure tags without alt text will get description of image.

```bash
docker run -v $(pwd):/data -w /data --rm pdfix/alt-text-vision:latest generate-alt-text -i input.pdf -o output.pdf
```

With PDFix License add these arguments.

```bash
--name ${LICENSE_NAME} --key ${LICENSE_KEY}
```

You can also generate alt text just for one image using this example:

```bash
docker run -v $(pwd):/data -w /data --rm pdfix/alt-text-vision:latest generate-alt-text -i image.jpg -o output.txt
```

For more detailed information about the available command-line arguments, you can run the following command:

```bash
docker run --rm pdfix/alt-text-vision:latest --help
```

## Exporting Configuration for Integration

To export the configuration JSON file, use the following command:

```bash
docker run -v $(pwd):/data -w /data --rm pdfix/alt-text-vision:latest config -o config.json
```

## License

- PDFix license https://pdfix.net/terms

Trial version of the PDFix SDK may apply a watermark on the page and redact random parts of the PDF including the scanned image in background. Contact us to get an evaluation or production license.

## Help & Support

To obtain a PDFix SDK license or report an issue please contact us at support@pdfix.net.
For more information visit https://pdfix.net
