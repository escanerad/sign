# Copyright 2023 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json

from odoo.tests.common import HttpCase, tagged

from .common import SignOcaCommon


@tagged("post_install", "-at_install")
class TestSignPortal(SignOcaCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal User",
                "login": "portal",
                "password": "portal",
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )
        cls.signer = cls.env["res.partner"].create({"name": "Signer"})
        cls.request = cls.env["sign.oca.request"].create(
            {
                "data": cls.data,
                "name": "Demo template",
                "signer_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": cls.signer.id,
                            "role_id": cls.role_customer.id,
                        },
                    )
                ],
            }
        )
        cls.item = cls.request.add_item(
            {
                "role_id": cls.role_customer.id,
                "field_id": cls.env.ref("sign_oca.sign_field_name").id,
                "page": 1,
                "position_x": 10,
                "position_y": 10,
                "width": 10,
                "height": 10,
            }
        )
        cls.request.action_send()
        cls.env.flush_all()
        cls.request.signer_ids.invalidate_recordset()

    def test_portal(self):
        self.authenticate("portal", "portal")
        self.url_open(self.request.signer_ids.access_url).raise_for_status()
        self.assertEqual(
            base64.b64decode(self.data),
            self.url_open(
                f"/sign_oca/content/{self.request.signer_ids.id}/{self.request.signer_ids.access_token}"
            ).content,
        )
        self.assertEqual(
            self.url_open(
                f"/sign_oca/info/{self.request.signer_ids.id}/{self.request.signer_ids.access_token}",
                data="{}",
                headers={"Content-Type": "application/json"},
            ).json()["result"]["items"][str(self.item["id"])],
            self.item,
        )
        data = {}
        for key in self.request.signer_ids.get_info()["items"]:
            val = self.request.signer_ids.get_info()["items"][key].copy()
            val["value"] = "My Name"
            data[key] = val


SIGN_PAGE_CHECK = """
const start = Date.now();
function step() {
    const iframe = document.querySelector("iframe.o_sign_oca_iframe");
    const doc = iframe && iframe.contentDocument;
    const viewer = doc && doc.getElementById("viewer");
    const input = doc && doc.querySelector(".o_sign_oca_field input");
    if (viewer && viewer.classList.contains("sign_oca_ready") && input) {
        const button = document.getElementById("sign_oca_button");
        if (!button || !button.disabled) {
            console.error("The sign button is enabled before the required field is filled");
            return;
        }
        input.value = "Synthetic signer";
        input.dispatchEvent(new Event("change"));
        if (button.disabled) {
            console.error("The sign button is still disabled once the field is filled");
            return;
        }
        console.log("test successful");
        return;
    }
    if (Date.now() - start > 50000) {
        console.error(
            "The PDF viewer did not get ready with its fields: " +
                JSON.stringify({
                    iframe: Boolean(iframe),
                    viewer: viewer && viewer.className,
                    pages: doc ? doc.getElementsByClassName("page").length : -1,
                    fields: doc ? doc.querySelectorAll(".o_sign_oca_field").length : -1,
                    error: doc && doc.getElementById("errorWrapper") && doc.getElementById("errorWrapper").textContent,
                })
        );
        return;
    }
    setTimeout(step, 200);
}
step();
"""


@tagged("post_install", "-at_install")
class TestSignPortalBrowser(SignOcaCommon, HttpCase):
    """The portal pages and the signing page in a browser (no jQuery since Odoo 20)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Portal Signer",
                    "login": "portal_signer",
                    "password": "portal_signer",
                    "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
                }
            )
        )
        cls.request = cls.env["sign.oca.request"].create(
            {
                "data": cls.data,
                "name": "Demo template",
                "signer_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": cls.portal_user.partner_id.id,
                            "role_id": cls.role_customer.id,
                        },
                    )
                ],
            }
        )
        cls.request.add_item(
            {
                "role_id": cls.role_customer.id,
                "field_id": cls.env.ref("sign_oca.sign_field_name").id,
                "page": 1,
                "position_x": 10,
                "position_y": 10,
                "width": 20,
                "height": 5,
                "required": True,
            }
        )
        cls.request.action_send()

    def test_portal_tours(self):
        self.start_tour("/my", "test_sign_tour", login="portal_signer")
        self.start_tour("/my/sign_requests", "test_sign_doc_tour", login="portal_signer")

    def test_sign_page(self):
        signer = self.request.signer_ids
        self.browser_js(
            signer.access_url,
            SIGN_PAGE_CHECK,
            login="portal_signer",
        )


CONFIGURE_CHECK = """
const start = Date.now();
Promise.resolve()
    .then(() => odoo.__WOWL_DEBUG__.root.env.services.action.doAction(%(action)s))
    .catch((error) => console.error("The configuration action failed: " + error + (error && error.stack)));
function step() {
    const iframe = document.querySelector(".o_action_manager iframe.o_sign_oca_iframe");
    const doc = iframe && iframe.contentDocument;
    const viewer = doc && doc.getElementById("viewer");
    const field = doc && doc.querySelector(".o_sign_oca_field .o_sign_oca_draggable");
    if (viewer && viewer.classList.contains("sign_oca_ready") && field) {
        console.log("test successful");
        return;
    }
    if (Date.now() - start > 50000) {
        console.error(
            "The configuration screen did not show the template field: " +
                JSON.stringify({
                    iframe: Boolean(iframe),
                    viewer: viewer && viewer.className,
                    pages: doc ? doc.getElementsByClassName("page").length : -1,
                    fields: doc ? doc.querySelectorAll(".o_sign_oca_field").length : -1,
                    action: (document.querySelector(".o_action_manager") || {}).className,
                    content: (document.querySelector(".o_action_manager") || document.body).innerHTML.slice(0, 400),
                })
        );
        return;
    }
    setTimeout(step, 200);
}
step();
"""


@tagged("post_install", "-at_install")
class TestSignConfigureBrowser(SignOcaCommon, HttpCase):
    """The backend screen to place the fields of a template (OWL 3 since Odoo 20)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["sign.oca.template"].create(
            {"data": cls.data, "name": "Demo template", "filename": "empty.pdf"}
        )
        cls.env.ref("base.user_admin").group_ids += cls.env.ref("sign_oca.sign_oca_group_admin")
        cls.template.add_item(
            {
                "field_id": cls.env.ref("sign_oca.sign_field_name").id,
                "page": 1,
                "position_x": 10,
                "position_y": 10,
                "width": 20,
                "height": 5,
            }
        )

    def test_configure_screen(self):
        action = json.dumps(self.template.configure())
        self.browser_js(
            "/odoo",
            CONFIGURE_CHECK % {"action": action},
            ready="odoo.isReady",
            login="admin",
        )
