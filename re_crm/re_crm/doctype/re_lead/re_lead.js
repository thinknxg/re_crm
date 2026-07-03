frappe.ui.form.on("RE Lead", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.deal &&
			!["Converted", "Disqualified"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Create Deal"), () =>
				frm.call("make_deal").then((r) =>
					frappe.set_route("Form", "RE Deal", r.message))
			).addClass("btn-primary");
		}
		if (!frm.is_new() && frm.doc.status === "New") {
			frm.add_custom_button(__("Mark Contacted"), () => {
				frm.set_value("status", "Contacted");
				frm.save();
			});
		}
	},
});
