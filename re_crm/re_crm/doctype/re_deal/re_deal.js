frappe.ui.form.on("RE Deal", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.unit &&
			!["Won", "Lost"].includes(frm.doc.pipeline_stage) && !frm.doc.reservation) {
			frm.add_custom_button(__("Reserve Unit"), () => {
				frappe.new_doc("Reservation", { deal: frm.doc.name, unit: frm.doc.unit });
			}, __("Create"));
		}
		if (!frm.is_new() && frm.doc.unit &&
			["Negotiation", "Reservation"].includes(frm.doc.pipeline_stage)) {
			frm.add_custom_button(__("Lease Contract"), () => {
				frappe.new_doc("Lease Contract", { unit: frm.doc.unit });
			}, __("Create"));
		}
	},
});
