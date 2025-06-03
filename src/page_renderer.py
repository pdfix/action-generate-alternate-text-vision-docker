import ctypes

from pdfixsdk import (
    PdfDoc,
    PdfImageParams,
    Pdfix,
    PdfPageRenderParams,
    PdfRect,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kRotate0,
)


def render_part_of_page(pdfix: Pdfix, doc: PdfDoc, page_num: int, bbox: PdfRect, zoom: float) -> bytearray:
    """
    Render part of PDF page into image.

    Args:
        doc (PdfDox): PDF document.
        page_num (int): Page number.
        bbox (PdfRect): Bounding box.
        zoom (float): Render at zoom level.

    Returns:
        Rendered image data in bytearray.
    """
    page = doc.AcquirePage(page_num)
    try:
        page_view = page.AcquirePageView(zoom, kRotate0)
        try:
            rect = page_view.RectToDevice(bbox)

            # render content
            render_params = PdfPageRenderParams()
            try:
                render_params.matrix = page_view.GetDeviceMatrix()
                render_params.clip_box = bbox
                render_params.image = pdfix.CreateImage(
                    rect.right - rect.left,
                    rect.bottom - rect.top,
                    kImageDIBFormatArgb,
                )
                page.DrawContent(render_params)

                # save image to stream and data
                memory_stream = pdfix.CreateMemStream()
                try:
                    img_params = PdfImageParams()
                    img_params.format = kImageFormatJpg
                    render_params.image.SaveToStream(memory_stream, img_params)

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
