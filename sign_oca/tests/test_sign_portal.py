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
            console.error(
                "The sign button is enabled before the required field is filled"
            );
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
                    error:
                        doc &&
                        doc.getElementById("errorWrapper") &&
                        doc.getElementById("errorWrapper").textContent,
                })
        );
        return;
    }
    setTimeout(step, 200);
}
step();
"""


SIGN_DOCUMENT_CHECK = """
const start = Date.now();
let stage = "load";
function info(doc) {
    const modal = document.querySelector(".modal");
    return JSON.stringify({
        stage,
        fields: doc ? doc.querySelectorAll(".o_sign_oca_field").length : -1,
        text: doc && (doc.querySelector(".o_sign_oca_field input") || {}).value,
        image: Boolean(doc && doc.querySelector(".o_sign_oca_field img")),
        modal: modal && modal.innerText.slice(0, 200),
    });
}
function step() {
    const iframe = document.querySelector("iframe.o_sign_oca_iframe");
    const doc = iframe && iframe.contentDocument;
    const viewer = doc && doc.getElementById("viewer");
    const navigator = doc && doc.querySelector(".o_sign_sign_item_navigator");
    const button = document.getElementById("sign_oca_button");
    if (Date.now() - start > 80000) {
        console.error("The document could not be signed: " + info(doc));
        return;
    }
    if (stage === "load") {
        if (viewer && viewer.classList.contains("sign_oca_ready") && navigator) {
            // Go to the text field, focusing it fills it with the partner name
            navigator.click();
            stage = "text";
        }
    } else if (stage === "text") {
        const input = doc.querySelector(".o_sign_oca_field input");
        if (input && input.value) {
            // Go to the signature field, which opens the signature dialog
            navigator.click();
            stage = "dialog";
        }
    } else if (stage === "dialog") {
        const adopt = document.querySelector(".modal .modal-footer .btn-primary");
        if (adopt && !adopt.disabled) {
            adopt.click();
            stage = "sign";
        }
    } else if (stage === "sign") {
        if (doc.querySelector(".o_sign_oca_field img") && button && !button.disabled) {
            // The page is reloaded once signed: report the result of the call
            const open = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function (method, url) {
                if (String(url).includes("/sign_oca/sign/")) {
                    this.addEventListener("load", () => {
                        if (JSON.parse(this.responseText).error) {
                            console.error("Signing failed: " + this.responseText);
                        } else {
                            console.log("test successful");
                        }
                    });
                }
                return open.apply(this, arguments);
            };
            button.click();
            stage = "signing";
        }
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
        self.start_tour(
            "/my/sign_requests", "test_sign_doc_tour", login="portal_signer"
        )

    def test_sign_page(self):
        signer = self.request.signer_ids
        self.browser_js(
            signer.access_url,
            SIGN_PAGE_CHECK,
            login="portal_signer",
        )

    def test_sign_document(self):
        """Fill the fields with the navigator, adopt a signature and sign."""
        request = self.env["sign.oca.request"].create(
            {
                "data": self.data,
                "name": "Document to sign",
                "signer_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.portal_user.partner_id.id,
                            "role_id": self.role_customer.id,
                        },
                    )
                ],
            }
        )
        for field, position_y in (
            ("sign_field_name", 10),
            ("sign_field_signature", 40),
        ):
            request.add_item(
                {
                    "role_id": self.role_customer.id,
                    "field_id": self.env.ref(f"sign_oca.{field}").id,
                    "page": 1,
                    "position_x": 10,
                    "position_y": position_y,
                    "width": 20,
                    "height": 10,
                    "required": True,
                }
            )
        request.action_send()
        signer = request.signer_ids
        self.browser_js(
            signer.access_url,
            SIGN_DOCUMENT_CHECK,
            login="portal_signer",
            timeout=120,
        )
        signer.invalidate_recordset()
        self.assertTrue(signer.signed_on)
        self.assertEqual(request.state, "2_signed")


CONFIGURE_CHECK = """
const start = Date.now();
Promise.resolve()
    .then(() => odoo.__WOWL_DEBUG__.root.env.services.action.doAction(%(action)s))
    .catch((error) =>
        console.error(
            "The configuration action failed: " + error + (error && error.stack)
        )
    );
function step() {
    const iframe = document.querySelector(".o_action_manager iframe.o_sign_oca_iframe");
    const doc = iframe && iframe.contentDocument;
    const viewer = doc && doc.getElementById("viewer");
    const field = doc && doc.querySelector("%(selector)s");
    // The field (or its icon) must be displayed, not only be in the DOM
    if (
        viewer &&
        viewer.classList.contains("sign_oca_ready") &&
        field &&
        field.getBoundingClientRect().width > 0
    ) {
        console.log("test successful");
        return;
    }
    if (Date.now() - start > 50000) {
        const manager = document.querySelector(".o_action_manager");
        console.error(
            "The screen did not show the field: " +
                JSON.stringify({
                    iframe: Boolean(iframe),
                    viewer: viewer && viewer.className,
                    pages: doc ? doc.getElementsByClassName("page").length : -1,
                    fields: doc ? doc.querySelectorAll(".o_sign_oca_field").length : -1,
                    action: (manager || {}).className,
                    content: (manager || document.body).innerHTML.slice(0, 400),
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
        cls.env.ref("base.user_admin").group_ids += cls.env.ref(
            "sign_oca.sign_oca_group_admin"
        )
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
            CONFIGURE_CHECK
            % {
                "action": action,
                "selector": ".o_sign_oca_field .o_sign_oca_draggable",
            },
            ready="odoo.isReady",
            login="admin",
        )

    def test_preview_screen(self):
        request = self.env["sign.oca.request"].create(
            {
                "data": self.data,
                "name": "Demo request",
                "signer_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.partner.id,
                            "role_id": self.role_customer.id,
                        },
                    )
                ],
            }
        )
        request.add_item(
            {
                "role_id": self.role_customer.id,
                "field_id": self.env.ref("sign_oca.sign_field_name").id,
                "page": 1,
                "position_x": 10,
                "position_y": 10,
                "width": 20,
                "height": 5,
            }
        )
        action = json.dumps(request.preview())
        self.browser_js(
            "/odoo",
            CONFIGURE_CHECK % {"action": action, "selector": ".o_sign_oca_field"},
            ready="odoo.isReady",
            login="admin",
        )

    def test_systray(self):
        request = self.env["sign.oca.request"].create(
            {
                "data": self.data,
                "name": "Systray request",
                "signer_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.env.ref("base.partner_admin").id,
                            "role_id": self.role_customer.id,
                        },
                    )
                ],
            }
        )
        request.action_send()
        self.start_tour("/odoo", "test_sign_systray_tour", login="admin")
