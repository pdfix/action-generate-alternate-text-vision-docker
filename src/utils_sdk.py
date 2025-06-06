import re
from typing import Optional

from pdfixsdk import Pdfix, PdsStructElement, kPdsStructChildElement

from exceptions import PdfixException


def authorize_sdk(pdfix: Pdfix, license_name: Optional[str], license_key: Optional[str]) -> None:
    """
    Tries to authorize or activate Pdfix license.

    Args:
        pdfix (Pdfix): Pdfix sdk instance.
        license_name (string): Pdfix sdk license name (e-mail)
        license_key (string): Pdfix sdk license key
    """
    if license_name and license_key:
        authorization = pdfix.GetAccountAuthorization()
        if not authorization.Authorize(license_name, license_key):
            raise PdfixException(pdfix, "Failed to authorize acount")
    elif license_key:
        if not pdfix.GetStandarsAuthorization().Activate(license_key):
            raise PdfixException(pdfix, "Failed to activate acount")
    else:
        print("No license name or key provided. Using PDFix SDK trial")


def browse_tags_recursive(element: PdsStructElement, regex_tag: str) -> list[PdsStructElement]:
    """
    Recursively browses through the structure elements of a PDF document and processes
    elements that match the specified tags.

    Description:
    This function recursively browses through the structure elements of a PDF document
    starting from the specified parent element. It checks each child element to see if it
    matches the specified tags using a regular expression. If a match is found, the element
    is processed using the `process_struct_elem` function. If no match is found, the function
    calls itself recursively on the child element.

    Args:
        element (PdsStructElement): The parent structure element to start browsing from.
        regex_tag (str): The regular expression to match tags.
    """
    result = []
    count = element.GetNumChildren()
    structure_tree = element.GetStructTree()
    for i in range(0, count):
        if element.GetChildType(i) != kPdsStructChildElement:
            continue
        child_element: PdsStructElement = structure_tree.GetStructElementFromObject(element.GetChildObject(i))
        if re.match(regex_tag, child_element.GetType(True)) or re.match(regex_tag, child_element.GetType(False)):
            # process element
            result.append(child_element)
        else:
            result.extend(browse_tags_recursive(child_element, regex_tag))
    return result
