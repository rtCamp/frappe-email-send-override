import frappe
from frappe.utils import cint


class EmailAccountOverride:
    """Mixin for Email Account, registered through `extend_doctype_class`.

    It used to be an `override_doctype_class`. Frappe uses only one override class per
    DocType (from the app installed last), so it replaced Helpdesk's Email Account class
    and switched off Helpdesk's reply threading. A mixin is stacked on top of whichever
    class is active, so both work.
    """

    def sendmail_config(self):
        if (
            not hasattr(self, "custom_use_separate_credential_for_outgoing")
            or not self.custom_use_separate_credential_for_outgoing
        ):
            return super().sendmail_config()

        login_id = getattr(self, "login_id", None) or self.email_id
        password = self._password

        if self.custom_outgoing_server_username:
            login_id = self.custom_outgoing_server_username

        if self.custom_outgoing_server_password:
            raise_exception = not (self.no_smtp_authentication or frappe.flags.in_test)
            password = self.get_password(
                fieldname="custom_outgoing_server_password",
                raise_exception=raise_exception,
            )

        config = {
            "email_account": self.name,
            "server": self.smtp_server,
            "port": cint(self.smtp_port),
            "login": login_id,
            "password": password,
            "use_ssl": cint(self.use_ssl_for_outgoing),
            "use_tls": cint(self.use_tls),
            "use_oauth": False,
            "access_token": None,
        }
        if self.flags.validate_smtp_connection:
            config["timeout"] = 15
        return config
