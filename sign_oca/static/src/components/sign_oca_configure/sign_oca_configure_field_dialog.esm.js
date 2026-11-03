/* Copyright 2024 Tecnativa - Carlos Roca
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {Dialog} from "@web/core/dialog/dialog";
import {Component, signal, t, useProps} from "@odoo/owl";

const isValidTitle = (m) =>
    typeof m === "string" ||
    (typeof m === "object" && typeof m.toString === "function");

export class SignOcaConfigureFieldDialog extends Component {
    props = useProps({
        close: t.function(),
        title: t.customValidator(t.any(), isValidTitle),
        item: t.object(),
        info: t.object(),
        confirm: t.function(),
        delete: t.function(),
    });

    setup() {
        this.env.dialogData.dismiss = () => this._cancel();
        this.modalRef = signal.ref();
        this.isProcess = false;
    }

    async _cancel() {
        this.props.close();
    }

    async _confirm() {
        const el = this.modalRef();
        await this.props.confirm(
            parseInt(el.querySelector('select[name="field_id"]').value, 10),
            parseInt(el.querySelector('select[name="role_id"]').value, 10),
            el.querySelector("input[name='required']").checked,
            el.querySelector("input[name='placeholder']").value
        );
        this.props.close();
    }

    async _delete() {
        this.props.delete();
        this.props.close();
    }
}
SignOcaConfigureFieldDialog.template = "sign_oca.SignOcaConfigureFieldDialog";
SignOcaConfigureFieldDialog.components = {Dialog};
