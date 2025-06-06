import ctypes

from pdfixsdk import (
    PdfDevRect,
    PdfDoc,
    PdfImageParams,
    Pdfix,
    PdfPage,
    PdfPageRenderParams,
    PdfPageView,
    PdfRect,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kRotate0,
)

from exceptions import PdfixException


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
    page: PdfPage = doc.AcquirePage(page_num)
    if page is None:
        raise PdfixException(pdfix, "Unable to acquire the page")

    try:
        page_view: PdfPageView = page.AcquirePageView(zoom, kRotate0)
        if page_view is None:
            raise PdfixException(pdfix, "Unable to acquire page view")

        try:
            rect: PdfDevRect = page_view.RectToDevice(bbox)

            # render content
            render_params = PdfPageRenderParams()
            render_params.matrix = page_view.GetDeviceMatrix()
            render_params.clip_box = bbox
            render_params.image = pdfix.CreateImage(
                rect.right - rect.left,
                rect.bottom - rect.top,
                kImageDIBFormatArgb,
            )
            if render_params.image is None:
                raise PdfixException(pdfix, "Unable to create the image")

            try:
                if not page.DrawContent(render_params):
                    raise PdfixException(pdfix, "Unable to draw the content")

                # save image to stream and data
                memory_stream = pdfix.CreateMemStream()
                if memory_stream is None:
                    raise PdfixException(pdfix, "Unable to create memory stream")

                try:
                    img_params = PdfImageParams()
                    img_params.format = kImageFormatJpg

                    if not render_params.image.SaveToStream(memory_stream, img_params):
                        raise PdfixException(pdfix, "Unable to save the image to the stream")

                    data = bytearray(memory_stream.GetSize())
                    raw_data = (ctypes.c_ubyte * len(data)).from_buffer(data)
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
