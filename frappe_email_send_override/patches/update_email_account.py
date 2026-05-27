import frappe


def execute():
    accounts = frappe.get_all(
        "Email Account",
        filters={"custom_outgoing_server_username": ["is", "set"], "custom_outgoing_server_password": ["is", "set"]},
        pluck="name",
    )
    for account in accounts:
        frappe.db.set_value("Email Account", account, "custom_use_separate_credential_for_outgoing", 1)
