// Copyright (c) 2024, Upeosoft and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Whatsapp Settings", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Whatsapp Settings', {
    validate: function(frm) {
        frappe.call({
            method: 'whatsapp_integration.service.rest.set_whatsapp_webhook',
            args: {},
            callback: function(r) {
                if (r.message) {
                    frappe.msgprint(r.message);
                }
            }
        });
    }
});

