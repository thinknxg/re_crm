frappe.ui.form.on("Commission Entry", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Approved") {
			frm.add_custom_button(__("Mark Paid"), () =>
				frm.call("mark_paid").then(() => frm.reload_doc())
			).addClass("btn-success");
		}
	},
});
