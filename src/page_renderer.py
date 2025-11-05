import ctypes
from typing import Optional

from pdfixsdk import (
    PdfDevRect,
    PdfDoc,
    PdfImageParams,
    Pdfix,
    PdfPage,
    PdfPageRenderParams,
    PdfPageView,
    PdfRect,
    PsImage,
    PsMemoryStream,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kRotate0,
)

from exceptions import PdfixFailedToRenderException


def render_part_of_page(pdfix: Pdfix, doc: PdfDoc, page_num: int, bbox: PdfRect, zoom: float) -> bytearray:
    """
    Render part of PDF page into image.

    Args:
        pdfix (Pdfix): Pdfix SDK.
        doc (PdfDox): PDF document.
        page_num (int): Page number.
        bbox (PdfRect): Bounding box.
        zoom (float): Render at zoom level.

    Returns:
        Rendered image data in bytearray.
    """
    page: Optional[PdfPage] = doc.AcquirePage(page_num)
    if page is None:
        raise PdfixFailedToRenderException(pdfix, "Unable to acquire the page")

    try:
        page_view: Optional[PdfPageView] = page.AcquirePageView(zoom, kRotate0)
        if page_view is None:
            raise PdfixFailedToRenderException(pdfix, "Unable to acquire page view")

        try:
            rect: PdfDevRect = page_view.RectToDevice(bbox)

            # render content
            render_params: PdfPageRenderParams = PdfPageRenderParams()
            render_params.matrix = page_view.GetDeviceMatrix()
            render_params.clip_box = bbox
            ps_image: Optional[PsImage] = pdfix.CreateImage(
                rect.right - rect.left,
                rect.bottom - rect.top,
                kImageDIBFormatArgb,
            )
            if ps_image is None:
                raise PdfixFailedToRenderException(pdfix, "Unable to create the image")

            render_params.image = ps_image

            try:
                if not page.DrawContent(render_params):
                    raise PdfixFailedToRenderException(pdfix, "Unable to draw the content")

                # save image to stream and data
                memory_stream: Optional[PsMemoryStream] = pdfix.CreateMemStream()
                if memory_stream is None:
                    raise PdfixFailedToRenderException(pdfix, "Unable to create memory stream")

                try:
                    img_params: PdfImageParams = PdfImageParams()
                    img_params.format = kImageFormatJpg

                    if not render_params.image.SaveToStream(memory_stream, img_params):
                        raise PdfixFailedToRenderException(pdfix, "Unable to save the image to the stream")

                    data: bytearray = bytearray(memory_stream.GetSize())
                    raw_data: ctypes.Array[ctypes.c_ubyte] = (ctypes.c_ubyte * len(data)).from_buffer(data)
                    memory_stream.Read(0, raw_data, len(data))

                except Exception:
                    raise
                finally:
                    memory_stream.Destroy()
            except Exception:
                raise
            finally:
                render_params.image.Destroy()
        except Exception:
            raise
        finally:
            page_view.Release()
    except Exception:
        raise
    finally:
        page.Release()

    return data
