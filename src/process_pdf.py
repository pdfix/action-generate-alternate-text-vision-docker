import logging
import os
from pathlib import Path
from typing import Optional

from pdfixsdk import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfRect,
    PdfStructElemEnumProcType,
    PdfTemplateQuery,
    PdsArray,
    PdsDictionary,
    PdsObject,
    PdsStructElement,
    PdsStructTree,
    PsFileStream,
    kDataFormatJson,
    kEnumNone,
    kEnumResultContinue,
    kPdsStructChildElement,
    kPsReadOnly,
    kSaveFull,
)
from tqdm import tqdm

from exceptions import (
    PdfixFailedToLoadTemplateException,
    PdfixFailedToOpenException,
    PdfixFailedToSaveException,
    PdfixInitializeException,
    PdfixNoTagsException,
)
from logger import get_logger
from page_renderer import describe_blank_image, render_part_of_page
from utils_sdk import authorize_sdk
from vision import generate_alt_text_description

logger: logging.Logger = get_logger("app_logger")


# Part of the progress bar (10 % to 95 %) filled while tags are processed
PROCESSING_PROGRESS: float = 85.0


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
        regex_template: str | Path,
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
            regex_template (str | Path): Regex or path to template JSON for matching tags.
        """
        self.input_path: str = input_path
        self.output_path: str = output_path
        self.license_name: str = license_name
        self.license_key: str = license_key
        self.overwrite: bool = overwrite
        self.zoom: float = zoom
        self.model_path: str = model_path
        self.regex_template: str | Path = regex_template

        self.pdfix: Optional[Pdfix] = None
        self.doc: Optional[PdfDoc] = None
        self.struct_tree: Optional[PdsStructTree] = None
        self.template_query: Optional[PdfTemplateQuery] = None
        self.matching_tags: int = 0
        self.progress_bar: Optional[tqdm] = None
        self.progress_step: float = 0.0

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
                raise PdfixNoTagsException()

            self.template_query = self._load_template_query(self.doc)

            progress_bar.update(10)
            progress_bar.set_description("Processing elements")

            # Keep local references so the ctypes callbacks are not GC'd during enumeration.
            count_proc = PdfStructElemEnumProcType(self.count_matching_tags)
            enum_proc = PdfStructElemEnumProcType(self.enumerate_struct_tree)
            try:
                # Count matching tags first (cheap, no rendering) so every tag moves the progress by the same step
                self.matching_tags = 0
                self.doc.EnumStructTree(None, kEnumNone, count_proc, None)
                self.progress_bar = progress_bar
                self.progress_step = PROCESSING_PROGRESS / self.matching_tags if self.matching_tags > 0 else 0.0
                self.doc.EnumStructTree(None, kEnumNone, enum_proc, None)
            except Exception:
                raise
            finally:
                self.struct_tree = None
                self.template_query = None
                self.progress_bar = None

            progress_bar.n = 95
            progress_bar.set_description("Saving document")
            progress_bar.refresh()

            if not self.doc.Save(self.output_path, kSaveFull):
                raise PdfixFailedToSaveException(self.pdfix, self.output_path)

            progress_bar.n = 100
            progress_bar.set_description("Done")
            progress_bar.refresh()

    def _load_template_query(self, doc: PdfDoc) -> PdfTemplateQuery:
        """
        Load a PdfTemplateQuery from a regex string or a template JSON file.

        Args:
            doc (PdfDoc): Open PDF document.

        Returns:
            Loaded template query used to test structure elements.
        """
        if self.pdfix is None:
            raise PdfixInitializeException()

        template_query: Optional[PdfTemplateQuery] = doc.CreateTemplateQuery()
        if template_query is None:
            raise PdfixFailedToLoadTemplateException(self.pdfix, "Failed to create Template query")

        if isinstance(self.regex_template, str):
            if not template_query.LoadFromRegex(self.regex_template):
                raise PdfixFailedToLoadTemplateException(self.pdfix, "Failed to load template from regex")
        else:
            string_path: str = str(self.regex_template)
            stream: Optional[PsFileStream] = self.pdfix.CreateFileStream(string_path, kPsReadOnly)
            if stream is None:
                raise PdfixFailedToLoadTemplateException(self.pdfix, "Failed to create file stream for template")
            if not template_query.LoadFromStream(stream, kDataFormatJson):
                raise PdfixFailedToLoadTemplateException(self.pdfix, "Failed to load template from stream")

        return template_query

    def enumerate_struct_tree(self, document_pointer: int, parent_pointer: int, index: int, client_data: int) -> int:
        """
        Callback invoked for each struct element during struct tree enumeration.

        Args:
            document_pointer (int): Document pointer passed by PDFix SDK (unused).
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

        if self.template_query is None:
            logger.warning("Template query is not initialized")
            return kEnumResultContinue

        if not self.template_query.TestStructElement(struct_element):
            return kEnumResultContinue

        try:
            self.process_image(struct_element)
        finally:
            if self.progress_bar is not None:
                self.progress_bar.update(self.progress_step)
        return kEnumResultContinue

    def count_matching_tags(self, document_pointer: int, parent_pointer: int, index: int, client_data: int) -> int:
        """
        Callback for struct tree enumeration that counts tags matching the tag filter.

        Args:
            document_pointer (int): Document pointer passed by PDFix SDK (unused).
            parent_pointer (int): Parent struct element pointer, or 0 for the root.
            index (int): Child index under the parent.
            client_data (int): Client data pointer passed by PDFix SDK (unused).

        Returns:
            Enumeration result code; always continues to the next element.
        """
        struct_element: Optional[PdsStructElement] = self.resolve_struct_element(
            self.struct_tree, parent_pointer, index
        )
        if struct_element is not None and self.template_query is not None:
            if self.template_query.TestStructElement(struct_element):
                self.matching_tags += 1
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
        For given image tag element generate alt text description using Vision.

        Args:
            struct_element (PdsStructElement): Image element to generate alt text for.
        """
        element_object: Optional[PdsObject] = struct_element.GetObject()
        if element_object is None:
            logger.warning("image element has no object")
            return
        image_name: str = f"image_{element_object.GetId()}.jpg"

        # Resolve overwrite
        original_alt_text: str = struct_element.GetAlt()

        if not self.overwrite and original_alt_text:
            logger.info(f"{struct_element.GetType(True)} keeps its alternate text: '{original_alt_text}'")
            return

        # get the object page number (it may be written in child objects)
        page_num: int = struct_element.GetPageNumber(0)
        if page_num == -1:
            for i in range(0, struct_element.GetNumChildren()):
                page_num = struct_element.GetChildPageNumber(i)
                if page_num != -1:
                    break
        if page_num == -1:
            logger.warning(f"[{image_name}] image found but can't determine the page number")
            return

        # get image bbox from attributes, or from the tag content when the attribute is missing
        bbox: PdfRect = self._attribute_bbox(struct_element)
        if self._is_empty_bbox(bbox):
            bbox = struct_element.GetBBox(page_num)
        if self._is_empty_bbox(bbox):
            logger.warning(f"[{image_name}] image found but its area on the page is empty")
            return

        data: bytearray = render_part_of_page(self.pdfix, self.doc, page_num, bbox, self.zoom)
        with open(image_name, "wb") as bf:
            bf.write(data)

        try:
            # One colour area (white, empty frame) gets a plain description, BLIP would invent a scene
            blank_description: str = describe_blank_image(image_name)
            if blank_description:
                struct_element.SetAlt(blank_description)
                logger.info(f"{struct_element.GetType(True)} on page {page_num + 1}: '{blank_description}'")
                return

            # Use AI to get alt description
            alt_text_by_vission: str = generate_alt_text_description(image_name, self.model_path)
            struct_element.SetAlt(alt_text_by_vission)
            logger.info(f"{struct_element.GetType(True)} on page {page_num + 1}: '{alt_text_by_vission}'")
        except Exception:
            raise
        finally:
            os.remove(image_name)

    def _attribute_bbox(self, struct_element: PdsStructElement) -> PdfRect:
        """
        Bounding box from the BBox attribute of the tag.

        Args:
            struct_element (PdsStructElement): Tag with attributes.

        Returns:
            Bounding box, empty when the tag has no BBox attribute.
        """
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
        return bbox

    def _is_empty_bbox(self, bbox: PdfRect) -> bool:
        """
        Check if bounding box has no area.

        Args:
            bbox (PdfRect): Bounding box.

        Returns:
            True when width or height is zero.
        """
        return bbox.left == bbox.right or bbox.top == bbox.bottom
