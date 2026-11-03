# Copyright 2026 ESCÀNER Serveis TIC, Albert Pons Domenjó
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .common import SignOcaCommon


@tagged("post_install", "-at_install")
class TestSignFromTemplateBrowser(SignOcaCommon, HttpCase):
    """The «Sign from template» item of the Actions menu (forms and lists)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("base.user_admin").group_ids += cls.env.ref(
            "sign_oca.sign_oca_group_user"
        )
        cls.company_partner = cls.env["res.partner"].create(
            {"name": "Synthetic parent", "is_company": True}
        )
        cls.child_one, cls.child_two = cls.env["res.partner"].create(
            [
                {"name": "Synthetic child one", "parent_id": cls.company_partner.id},
                {"name": "Synthetic child two", "parent_id": cls.company_partner.id},
            ]
        )
        cls.template = cls.env["sign.oca.template"].create(
            {
                "data": cls.data,
                "name": "Synthetic partner template",
                "filename": "empty.pdf",
                "model_id": cls.env.ref("base.model_res_partner").id,
            }
        )
        cls.template.add_item(
            {
                "field_id": cls.env.ref("sign_oca.sign_field_name").id,
                "role_id": cls.role_child_partner.id,
                "page": 1,
                "position_x": 10,
                "position_y": 10,
                "width": 10,
                "height": 10,
            }
        )

    def _requests(self):
        return self.env["sign.oca.request"].search(
            [("template_id", "=", self.template.id)]
        )

    def _check_request(self, request, record):
        self.assertEqual(len(request), 1)
        self.assertEqual(request.record_ref, record)
        self.assertEqual(request.signer_ids.partner_id, self.company_partner)
        self.assertEqual(request.signer_ids.role_id, self.role_child_partner)
        self.assertEqual(request.data.content, self.template.data.content)
        self.assertEqual(request.state, "0_sent")

    def test_sign_from_template_form(self):
        self.start_tour(
            f"/odoo/res.partner/{self.child_one.id}",
            "test_sign_from_template_form_tour",
            login="admin",
        )
        self._check_request(self._requests(), self.child_one)

    def test_sign_from_template_list(self):
        self.start_tour(
            "/odoo/action-base.action_partner_form?view_type=list",
            "test_sign_from_template_list_tour",
            login="admin",
        )
        self._check_request(self._requests(), self.child_two)

    def test_sign_from_template_hidden(self):
        self.template.model_id = self.env.ref("base.model_res_users")
        self.start_tour(
            "/odoo/action-base.action_partner_form?view_type=list",
            "test_sign_from_template_hidden_tour",
            login="admin",
        )
        self.assertFalse(self._requests())
