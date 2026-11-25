# Copyright (c) 2026, rtCamp and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.model.base_document import _get_extended_class

from frappe_email_send_override.overrides.email_account import EmailAccountOverride

HOOK = "frappe_email_send_override.overrides.email_account.EmailAccountOverride"


class TestEmailAccountExtension(unittest.TestCase):
    def test_registered_as_extension_not_override(self):
        hooks = frappe.get_module("frappe_email_send_override.hooks")
        self.assertEqual(hooks.extend_doctype_class["Email Account"], HOOK)
        self.assertFalse(hasattr(hooks, "override_doctype_class"))

    def test_is_a_mixin(self):
        self.assertFalse(issubclass(EmailAccountOverride, EmailAccount))

    def _extend(self, base):
        """Build the class Frappe would build with this app's extension registered."""
        original = frappe.get_hooks

        def get_hooks(name=None, *args, **kwargs):
            if name == "extend_doctype_class":
                return {"Email Account": [HOOK]}
            return original(name, *args, **kwargs)

        with (
            patch("frappe.get_hooks", get_hooks),
            # get_attr refuses apps not installed on the test site; load the class directly.
            patch("frappe.get_attr", lambda path: EmailAccountOverride if path == HOOK else None),
        ):
            return _get_extended_class(base, "Email Account")

    def test_stacks_on_plain_email_account(self):
        cls = self._extend(EmailAccount)
        self.assertEqual(cls.__mro__[1:3], (EmailAccountOverride, EmailAccount))
        self.assertIs(cls.sendmail_config, EmailAccountOverride.sendmail_config)

    def test_stacks_on_helpdesk_class_and_keeps_its_threading(self):
        try:
            from helpdesk.overrides.email_account import CustomEmailAccount
        except ImportError:
            self.skipTest("helpdesk app not in this bench")

        cls = self._extend(CustomEmailAccount)
        self.assertTrue(issubclass(cls, CustomEmailAccount))
        # Inbound mail (and its References threading) still comes from Helpdesk;
        # outgoing SMTP config comes from this app.
        self.assertIs(cls.get_inbound_mails, CustomEmailAccount.get_inbound_mails)
        self.assertIs(cls.sendmail_config, EmailAccountOverride.sendmail_config)

    def test_falls_back_to_frappe_config_when_flag_is_off(self):
        cls = self._extend(EmailAccount)
        account = cls.__new__(cls)
        account.custom_use_separate_credential_for_outgoing = 0
        original = EmailAccount.sendmail_config
        EmailAccount.sendmail_config = lambda self: {"from": "frappe"}
        try:
            self.assertEqual(account.sendmail_config(), {"from": "frappe"})
        finally:
            EmailAccount.sendmail_config = original
