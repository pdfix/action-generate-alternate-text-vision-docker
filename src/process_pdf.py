import os
from typing import Optional

from pdfixsdk import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfRect,
    PdfStructElemEnumProcType,
    PdsArray,
    PdsDictionary,
    PdsObject,
    PdsStructElement,
    PdsStructTree,
    kEnumNone,
    kEnumResultContinue,
    kPdsStructChildElement,
    kSaveFull,
)
from tqdm import tqdm

from exceptions import (
    PdfixFailedToOpenException,
    PdfixFailedToSaveException,
    PdfixInitializeException,
    PdfixNoTagsException,
)
from page_renderer import render_part_of_page
from utils_sdk import authorize_sdk
from vision import generate_alt_text_description


class GenerateAltTextsInPdf:
    def __init__(
        self,
        input_path: str,
        output_path: str,
        license_name: str,
        license_key: str,
        overwrite: bool,
        zoom: float,
        model_path: str,
    ):
        """
        Initialize class for generating alternate text for images in a PDF document.

        Args:
            input_path (str): Input path to the PDF file.
            output_path (str): Output path for saving the PDF file.
            license_name (str): Pdfix SDK license name.
            license_key (str): Pdfix SDK license key.
            overwrite (bool): Overwrite alternate text if already present.
            zoom (float): Zoom level for rendering the page.
            model_path (str): Path to Vision model. Default value is "model".
        """
        self.input_path: str = input_path
        self.output_path: str = output_path
        self.license_name: str = license_name
        self.license_key: str = license_key
        self.overwrite: bool = overwrite
        self.zoom: float = zoom
        self.model_path: str = model_path

        self.pdfix: Optional[Pdfix] = None
        self.doc: Optional[PdfDoc] = None
        self.struct_tree: Optional[PdsStructTree] = None

    def generate_alt_texts_in_pdf(self) -> None:
        """
        Generate alternate text for images in a PDF document.
        """
        with tqdm(total=100) as progress_bar:
            progress_bar.set_description("Initializing")

            self.pdfix = GetPdfix()
            if self.pdfix is None:
                raise PdfixInitializeException()

            authorize_sdk(self.pdfix, self.license_name, self.license_key)

            # Open doc
            self.doc = self.pdfix.OpenDoc(self.input_path, "")
            if self.doc is None:
                raise PdfixFailedToOpenException(self.pdfix, self.input_path)

            # Enumerate struct tree
            self.struct_tree = self.doc.GetStructTree()
            if self.struct_tree is None:
                raise PdfixNoTagsException(self.pdfix)

            progress_bar.update(10)
            progress_bar.set_description("Processing elements")

            # Keep a local reference so the ctypes callback is not GC'd during enumeration.
            enum_proc = PdfStructElemEnumProcType(self.enumerate_struct_tree)
            try:
                self.doc.EnumStructTree(None, kEnumNone, enum_proc, None)
            except Exception:
                raise
            finally:
                self.struct_tree = None

            progress_bar.n = 95
            progress_bar.set_description("Saving document")
            progress_bar.refresh()

            if not self.doc.Save(self.output_path, kSaveFull):
                raise PdfixFailedToSaveException(self.pdfix, self.output_path)

            progress_bar.n = 100
            progress_bar.set_description("Done")
            progress_bar.refresh()

    def enumerate_struct_tree(self, documnet_pointer: int, parent_pointer: int, index: int, client_data: int) -> int:
        """
        Callback invoked for each struct element during struct tree enumeration.

        Args:
            documnet_pointer (int): Document pointer passed by PDFix SDK (unused).
            parent_pointer (int): Parent struct element pointer, or 0 for the root.
            index (int): Child index under the parent.
            client_data (int): Client data pointer passed by PDFix SDK (unused).

        Returns:
            Enumeration result code; always continues to the next element.
        """
        struct_element: Optional[PdsStructElement] = self.resolve_struct_element(
            self.struct_tree, parent_pointer, index
        )
        if struct_element is None:
            return kEnumResultContinue

        if struct_element.GetType(False) == "Figure":
            self.process_image(struct_element)

        return kEnumResultContinue

    def resolve_struct_element(
        self, struct_tree: PdsStructTree, parent_pointer: int, index: int
    ) -> Optional[PdsStructElement]:
        """
        Resolve a struct element from enumeration parent pointer and child index.

        Args:
            struct_tree (PdsStructTree): Document struct tree.
            parent_pointer (int): Parent struct element pointer, or 0 for the root.
            index (int): Child index under the parent.

        Returns:
            Resolved struct element, or None if the child is not a struct element.
        """
        parent: PdsStructElement
        if parent_pointer:
            parent = PdsStructElement(parent_pointer)
        else:
            root_object: Optional[PdsObject] = struct_tree.GetObject()
            if root_object is None:
                return None
            root_element: Optional[PdsStructElement] = struct_tree.GetStructElementFromObject(root_object)
            if root_element is None:
                return None
            parent = root_element

        if parent.GetChildType(index) != kPdsStructChildElement:
            return None

        child_object: Optional[PdsObject] = parent.GetChildObject(index)
        if child_object is None:
            return None

        return struct_tree.GetStructElementFromObject(child_object)

    def process_image(self, struct_element: PdsStructElement) -> None:
        """
        For given image tag element generate alt text description using vision.

        Args:
            elem (PdsStructElement): Image element to generate alt text for.
        """
        element_object: Optional[PdsObject] = struct_element.GetObject()
        if element_object is None:
            print("image element has no object")
            return
        image_name: str = f"image_{element_object.GetId()}.jpg"

        # Resolve overwrite
        original_alt_text: str = struct_element.GetAlt()

        if not self.overwrite and original_alt_text:
            return

        # get image bbox from attributes
        bbox: PdfRect = PdfRect()
        for i in range(0, struct_element.GetNumAttrObjects()):
            attr_object: Optional[PdsObject] = struct_element.GetAttrObject(i)
            if attr_object is None:
                continue
            attr: PdsDictionary = PdsDictionary(attr_object.obj)
            arr: Optional[PdsArray] = attr.GetArray("BBox")
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
        page_num: int = struct_element.GetPageNumber(0)
        if page_num == -1:
            for i in range(0, struct_element.GetNumChildren()):
                page_num = struct_element.GetChildPageNumber(i)
                if page_num != -1:
                    break
        if page_num == -1:
            print(f"[{image_name}] image found but can't determine the page number")
            return

        data: bytearray = render_part_of_page(self.pdfix, self.doc, page_num, bbox, self.zoom)
        with open(image_name, "wb") as bf:
            bf.write(data)

        try:
            # Use AI to get alt description
            response: list[str] = generate_alt_text_description(image_name, self.model_path)
            alt_text_by_vission: str = response[0]
            struct_element.SetAlt(alt_text_by_vission)
        except Exception:
            raise
        finally:
            os.remove(image_name)
