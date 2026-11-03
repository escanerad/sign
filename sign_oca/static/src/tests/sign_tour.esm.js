/* Copyright 2025 Kencove - Mohamed Alkobrosli
   License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */
import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("test_sign_tour", {
    url: "/my",
    steps: () => [
        {
            content: "The portal home lists the signature requests",
            trigger: "a[href='/my/sign_requests']",
        },
    ],
});

registry.category("web_tour.tours").add("test_sign_doc_tour", {
    url: "/my/sign_requests",
    steps: () => [
        {
            content: "The request to sign is listed",
            trigger: "td a",
        },
    ],
});

// The Actions menu: a dropdown in lists, the cog menu in forms.
const ACTIONS_LIST = ".o_cp_action_menus .o-dropdown:contains(Actions)";
const ACTIONS_FORM = ".o_cp_action_menus button[aria-label='Actions menu']";

function signFromTemplateOpenMenu(trigger) {
    return [{content: "Open the Actions menu", trigger, run: "click"}];
}

function signFromTemplateSteps(actionsTrigger) {
    return [
        ...signFromTemplateOpenMenu(actionsTrigger),
        {
            content: "Sign from template",
            trigger: ".o-dropdown-item:contains(Sign from template)",
            run: "click",
        },
        {
            content: "Choose the template",
            trigger: ".modal .o_field_widget[name=template_id] input",
            run: "edit Synthetic partner template",
        },
        {
            trigger:
                ".o-autocomplete--dropdown-item:contains(Synthetic partner template)",
            run: "click",
        },
        {
            content: "Generate the requests",
            trigger: ".modal button[name=generate]",
            run: "click",
        },
        {
            content: "The wizard is closed",
            trigger: "body:not(:has(.modal))",
        },
    ];
}

const selectChildTwo = {
    content: "Select the second record",
    trigger: ".o_data_row:contains(Synthetic child two) .o_list_record_selector input",
    run: "click",
};

registry.category("web_tour.tours").add("test_sign_from_template_form_tour", {
    steps: () => signFromTemplateSteps(ACTIONS_FORM),
});

registry.category("web_tour.tours").add("test_sign_from_template_list_tour", {
    steps: () => [selectChildTwo, ...signFromTemplateSteps(ACTIONS_LIST)],
});

registry.category("web_tour.tours").add("test_sign_from_template_hidden_tour", {
    steps: () => [
        selectChildTwo,
        ...signFromTemplateOpenMenu(ACTIONS_LIST),
        {
            content: "The menu is open",
            trigger: ".o-dropdown-item:contains(Export)",
        },
        {
            content: "No «Sign from template» without a template for the model",
            trigger: "body:not(:has(.o-dropdown-item:contains(Sign from template)))",
        },
    ],
});
