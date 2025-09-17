import os

from pdfixsdk.Pdfix import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfRect,
    PdsDictionary,
    PdsStructElement,
    kSaveFull,
)

from exceptions import PdfixException
from page_renderer import render_part_of_page
from utils_sdk import authorize_sdk, browse_tags_recursive
from vision import generate_alt_text_description


def generate_alt_texts_in_pdf(
    input_path: str,
    output_path: str,
    license_name: str,
    license_key: str,
    overwrite: bool,
    zoom: float,
    model_path: str,
) -> None:
    """
    Run detect images and on those images run vission generate alt text.

    Args:
        input_path (str): Input path to the PDF file.
        output_path (str): Output path for saving the PDF file.
        license_name (str): Pdfix SDK license name.
        license_key (str): Pdfix SDK license key.
        overwrite (bool): Overwrite alternate text if already present.
        zoom (float): Zoom level for rendering the page.
        model_path (str): Path to Vision model. Default value is "model".
    """
    pdfix = GetPdfix()
    if pdfix is None:
        raise Exception("Pdfix Initialization fail")

    authorize_sdk(pdfix, license_name, license_key)

    # Open doc
    doc = pdfix.OpenDoc(input_path, "")
    if doc is None:
        raise PdfixException(pdfix, "Unable to open PDF")

    struct_tree = doc.GetStructTree()
    if struct_tree is None:
        raise PdfixException(pdfix, "PDF has no structure tree")

    child_element = struct_tree.GetStructElementFromObject(struct_tree.GetChildObject(0))
    try:
        items = browse_tags_recursive(child_element, "Figure")
        for element in items:
            process_image(pdfix, element, doc, overwrite, zoom, model_path)
    except Exception:
        raise

    if not doc.Save(output_path, kSaveFull):
        raise PdfixException("Unable to save PDF")


def process_image(
    pdfix: Pdfix, elem: PdsStructElement, doc: PdfDoc, overwrite: bool, zoom: float, model_path: str
) -> None:
    """
    For given image tag element generate alt text description using vision.

    Args:
        pdfix (Pdfix): Pdfix SDK.
        elem (PdsStructElement): Image element to generate alt text for.
        doc (PdfDoc): PDF document.
        overwrite (bool): Should original alt text be overwritten?
        zoom (float): Zoom level for rendering the page.
        model_path (str): Path to Vision model. Default value is "model".
    """
    image_name = f"image_{elem.GetObject().GetId()}.jpg"

    # get image bbox from attributes
    bbox = PdfRect()
    for i in range(0, elem.GetNumAttrObjects()):
        attr = PdsDictionary(elem.GetAttrObject(i).obj)
        arr = attr.GetArray("BBox")
        if not arr:
            continue
        bbox.left = arr.GetNumber(0)
        bbox.bottom = arr.GetNumber(1)
        bbox.right = arr.GetNumber(2)
        bbox.top = arr.GetNumber(3)
        break

    # check bounding box
    if bbox.left == bbox.right or bbox.top == bbox.bottom:
        print(f"[{image_name}] image found but no BBox attribute was set")
        return

    # get the object page number (it may be written in child objects)
    page_num = elem.GetPageNumber(0)
    if page_num == -1:
        for i in range(0, elem.GetNumChildren()):
            page_num = elem.GetChildPageNumber(i)
            if page_num != -1:
                break
    if page_num == -1:
        print(f"[{image_name}] image found but can't determine the page number")
        return

    data = render_part_of_page(pdfix, doc, page_num, bbox, zoom)
    with open(image_name, "wb") as bf:
        bf.write(data)

    try:
        # Use AI to get alt description
        response = generate_alt_text_description(image_name, model_path)

        alt_text_by_vission = response[0]
        original_alt_text = elem.GetAlt()

        if overwrite or not original_alt_text:
            elem.SetAlt(alt_text_by_vission)
    except Exception:
        raise
    finally:
        os.remove(image_name)
