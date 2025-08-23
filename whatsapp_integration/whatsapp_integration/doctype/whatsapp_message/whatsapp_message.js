// Copyright (c) 2024, Upeosoft and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Whatsapp Message', {
//     subject: function(frm) {
//         if (frm.doc.subject) {
//             frappe.db.get_value('Whatsapp Message Template', {subject: frm.doc.subject}, 'message')
//             .then(r => {
//                 let message = r.message;
//                 if (message) {
//                     frm.set_value('message_to_send', message.message);
//                 } else {
//                     frm.set_value('message_to_send', '');
//                 }
//             });
//         } else {
//             frm.set_value('message_to_send', '');
//         }
//     }
// });
