import {FormController} from "@web/views/form/form_controller";
import {ListController} from "@web/views/list/list_controller";
import {_t} from "@web/core/l10n/translation";
import {onWillStart} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {user} from "@web/core/user";

export function patchControllerSignOca() {
    return {
        setup() {
            super.setup(...arguments);
            this.showSignOcaTemplateGenerateMulti = false;
            onWillStart(() => this._showSignOcaTemplateGenerateMulti());
        },
        async _showSignOcaTemplateGenerateMulti() {
            if (await user.hasGroup("sign_oca.sign_oca_group_user")) {
                const templateCount = await this.orm.searchCount("sign.oca.template", [
                    ["model", "=", this.props.resModel],
                ]);
                this.showSignOcaTemplateGenerateMulti = templateCount !== 0;
            }
        },
        async _getSignOcaResIds() {
            const root = this.model.root;
            if (root.getResIds) {
                return root.getResIds(true);
            }
            return root.resId ? [root.resId] : [];
        },
        async _actionSignOcaTemplateGenerateMulti() {
            const resIds = await this._getSignOcaResIds();
            return this.actionService.doAction(
                "sign_oca.sign_oca_template_generate_multi_act_window",
                {
                    additionalContext: {
                        model: this.props.resModel,
                        active_ids: resIds,
                    },
                }
            );
        },
        getStaticActionMenuItems() {
            const menuItems = super.getStaticActionMenuItems(...arguments);
            menuItems.signOcaTemplateGenerateMulti = {
                isAvailable: () => this.showSignOcaTemplateGenerateMulti,
                sequence: 60,
                icon: "edit",
                description: _t("Sign from template"),
                callback: () => this._actionSignOcaTemplateGenerateMulti(),
            };
            return menuItems;
        },
    };
}

patch(ListController.prototype, patchControllerSignOca());
patch(FormController.prototype, patchControllerSignOca());
