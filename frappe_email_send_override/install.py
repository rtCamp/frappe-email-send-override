from frappe_email_send_override.setup import install


def after_install() -> None:
    """Create the app's custom fields when it is installed on a site."""
    install()
