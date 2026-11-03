# Copyright 2026 ESCÀNER Serveis TIC, Albert Pons Domenjó
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from io import BytesIO

from PIL import Image
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.pdfgen import canvas

from odoo.tools.pdf import PdfReader

from odoo.addons.base.tests.common import BaseCommon

from .common import SignOcaCommon

PAGE_SIZES = [A4, landscape(A4), letter]


def _source_pdf():
    """Three pages of different sizes, each with its own label."""
    stream = BytesIO()
    can = canvas.Canvas(stream)
    for number, size in enumerate(PAGE_SIZES, start=1):
        can.setPageSize(size)
        can.drawString(72, 72, f"Source page {number}")
        can.showPage()
    can.save()
    return stream.getvalue()


def _signature_png():
    stream = BytesIO()
    Image.new("RGB", (40, 20), (0, 0, 128)).save(stream, format="PNG")
    return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode()


def _images(page):
    xobjects = page["/Resources"].get("/XObject") or {}
    return [
        name
        for name, obj in xobjects.items()
        if obj.get_object().get("/Subtype") == "/Image"
    ]


class TestSignPdf(SignOcaCommon, BaseCommon):
    """The signed PDF keeps its pages and sizes; each field lands on its page."""

    _test_user_groups = (
        "base.group_user",
        "base.group_partner_manager",
        "sign_oca.sign_oca_group_admin",
    )

    def test_signed_pdf_pages(self):
        source = _source_pdf()
        signer_partner = self.env["res.partner"].create(
            {"name": "Synthetic signer", "email": "signer@example.com"}
        )
        request = self.env["sign.oca.request"].create(
            {
                "data": base64.b64encode(source).decode(),
                "name": "Three pages",
                "signer_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": signer_partner.id,
                            "role_id": self.role_customer.id,
                        },
                    )
                ],
            }
        )
        geometry = {
            "position_x": 20,
            "position_y": 30,
            "width": 20,
            "height": 10,
            "role_id": self.role_customer.id,
        }
        fields = [
            ("sign_oca.sign_field_signature", 1, _signature_png()),
            ("sign_oca.sign_field_name", 2, "Synthetic Name"),
            ("sign_oca.sign_field_check", 3, True),
        ]
        for xmlid, page, _value in fields:
            request.add_item(dict(geometry, field_id=self.env.ref(xmlid).id, page=page))
        request.action_send()
        signer = request.signer_ids
        items = {}
        for key, item in signer.get_info()["items"].items():
            value = next(v for x, p, v in fields if p == item["page"])
            items[key] = dict(item, value=value)
        signer.action_sign(items)

        original = PdfReader(BytesIO(source))
        signed = PdfReader(BytesIO(request.data.content))
        self.assertEqual(len(signed.pages), len(PAGE_SIZES))
        for number, (before, after) in enumerate(
            zip(original.pages, signed.pages, strict=True), start=1
        ):
            self.assertEqual(
                [float(v) for v in after.mediabox],
                [float(v) for v in before.mediabox],
                f"page {number} size changed",
            )
            self.assertIn(f"Source page {number}", after.extract_text())
        page_1, page_2, page_3 = signed.pages
        # The signature image is on page 1 only, the text on page 2 only.
        self.assertTrue(_images(page_1))
        self.assertFalse(_images(page_2))
        self.assertFalse(_images(page_3))
        self.assertIn("Synthetic Name", page_2.extract_text())
        self.assertNotIn("Synthetic Name", page_1.extract_text())
        self.assertNotIn("Synthetic Name", page_3.extract_text())
        # The check box (lines, no text) is drawn on page 3: its content grew.
        self.assertGreater(
            len(page_3.get_contents().get_data()),
            len(original.pages[2].get_contents().get_data()),
        )
        self.assertEqual(request.state, "2_signed")
