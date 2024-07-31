from frappe.utils import cint
import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount


class EmailAccountOverride(EmailAccount):
    def sendmail_config(self):
        oauth_token = self.get_oauth_token()
        login_id = getattr(self, "login_id", None) or self.email_id
        password = self._password

        if self.custom_outgoing_server_username:
            login_id = self.custom_outgoing_server_username

        if self.custom_outgoing_server_password:
            raise_exception = not (
                self.auth_method == "OAuth"
                or self.no_smtp_authentication
                or frappe.flags.in_test
            )
            password = self.get_password(
                fieldname="custom_outgoing_server_password",
                raise_exception=raise_exception,
            )

        return {
            "email_account": self.name,
            "server": self.smtp_server,
            "port": cint(self.smtp_port),
            "login": login_id,
            "password": password,
            "use_ssl": cint(self.use_ssl_for_outgoing),
            "use_tls": cint(self.use_tls),
            "use_oauth": self.auth_method == "OAuth",
            "access_token": (
                oauth_token.get_password("access_token") if oauth_token else None
            ),
        }
