import frappe
import json
import smtplib


def serialize_obj(obj):
    """Custom serialization for object for debugging purpose."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    try:
        return json.dumps(obj.__dict__)
    except TypeError:
        return str(obj)


def send(self, sender, recipient, msg):
    frappe.utils.logger.set_log_level("DEBUG")
    logger = frappe.logger("email_send_override")
    logger.debug("[RTCAMP] Email inner Send Override")

    # Serialize self object and log it
    logger.debug(f"[RTCAMP] Serialized self: {serialize_obj(self)}")

    # fetch frappe single doctype called smtp-settings
    settings = frappe.get_doc("SMTP Settings")
    logger.debug(serialize_obj(settings))
    logger.debug(settings.smtp_enable)
    logger.debug(settings.smtp_host)
    logger.debug(settings.smtp_port)
    logger.debug(settings.smtp_username)
    logger.debug(settings.smtp_password)

    # TODO :: if not enabled, fallback to original email sending
    if not settings.smtp_enable:
        return False

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(sender, recipient, msg)  # Send the email
        server.quit()  # Close the connection
        self.update_status("Sent")
    except Exception as e:
        self.update_status("Error")
        logger.debug("[RTCAMP] Email Failed")
        logger.debug(serialize_obj(e))
