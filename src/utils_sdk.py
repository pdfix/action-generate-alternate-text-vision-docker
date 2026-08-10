from typing import Optional

from pdfixsdk import (
    Pdfix,
    PsAccountAuthorization,
    PsStandardAuthorization,
)

from exceptions import PdfixActivationException, PdfixAuthorizationException


def authorize_sdk(pdfix: Pdfix, license_name: Optional[str], license_key: Optional[str]) -> None:
    """
    Tries to authorize or activate Pdfix license.

    Args:
        pdfix (Pdfix): Pdfix sdk instance.
        license_name (string): Pdfix sdk license name (e-mail)
        license_key (string): Pdfix sdk license key
    """
    if license_name and license_key:
        authorization: Optional[PsAccountAuthorization] = pdfix.GetAccountAuthorization()
        if authorization is None or not authorization.Authorize(license_name, license_key):
            raise PdfixAuthorizationException(pdfix)
    elif license_key:
        standard_authorization: Optional[PsStandardAuthorization] = pdfix.GetStandardAuthorization()
        if standard_authorization is None or not standard_authorization.Activate(license_key):
            raise PdfixActivationException(pdfix)
    else:
        print("No license name or key provided. Using PDFix SDK trial")
