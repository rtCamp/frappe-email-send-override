from unittest.mock import PropertyMock, patch

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.tests import IntegrationTestCase

from frappe_email_send_override.overrides.email_account import EmailAccountOverride


def _build_account(**overrides):
    """Build a minimal EmailAccountOverride instance for sendmail_config testing without going through Frappe doc machinery. _password is a property on EmailAccount and is not set here; callers that need it should patch it via PropertyMock."""
    account = EmailAccountOverride.__new__(EmailAccountOverride)
    account.name = overrides.get("name", "Test Account")
    account.email_id = overrides.get("email_id", "test@example.com")
    account.login_id = overrides.get("login_id", None)
    account.smtp_server = overrides.get("smtp_server", "smtp.example.com")
    account.smtp_port = overrides.get("smtp_port", 587)
    account.use_ssl_for_outgoing = overrides.get("use_ssl_for_outgoing", 0)
    account.use_tls = overrides.get("use_tls", 1)
    account.no_smtp_authentication = overrides.get("no_smtp_authentication", 0)
    account.flags = frappe._dict()
    # The override code unconditionally accesses these two attrs, so they must always exist on the stub.
    account.custom_outgoing_server_username = overrides.get("custom_outgoing_server_username", "")
    account.custom_outgoing_server_password = overrides.get("custom_outgoing_server_password", "")
    # The toggle is set conditionally so AC tests can exercise the "attr missing on legacy row" branch.
    if "custom_use_separate_credential_for_outgoing" in overrides:
        account.custom_use_separate_credential_for_outgoing = overrides["custom_use_separate_credential_for_outgoing"]
    return account


class TestSendmailConfigToggleOff(IntegrationTestCase):
    def test_toggle_off_returns_super_config(self):
        """When the toggle is 0, sendmail_config delegates to the parent class's sendmail_config."""
        account = _build_account(custom_use_separate_credential_for_outgoing=0)
        sentinel = {"from_super": True}

        with patch.object(EmailAccount, "sendmail_config", return_value=sentinel) as mock_super:
            config = account.sendmail_config()

        self.assertEqual(config, sentinel)
        mock_super.assert_called_once()

    def test_missing_toggle_attr_returns_super_config(self):
        """When the toggle attribute does not exist on the doc at all (legacy row), sendmail_config still delegates to the parent."""
        account = _build_account()  # toggle attr never set
        sentinel = {"legacy": True}

        with patch.object(EmailAccount, "sendmail_config", return_value=sentinel) as mock_super:
            config = account.sendmail_config()

        self.assertEqual(config, sentinel)
        mock_super.assert_called_once()


class TestSendmailConfigCredentialSelection(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        # _password is a property without a setter, so we mock it at the class level for the duration of each test.
        password_patcher = patch.object(
            EmailAccount, "_password", new_callable=PropertyMock, return_value="primary-password"
        )
        password_patcher.start()
        self.addCleanup(password_patcher.stop)

    def test_toggle_on_no_custom_uses_standard_credentials(self):
        """Toggle on but no custom credentials: login falls back to login_id/email_id, password to _password."""
        account = _build_account(custom_use_separate_credential_for_outgoing=1)

        config = account.sendmail_config()

        # login_id was None, so the override falls back to email_id
        self.assertEqual(config["login"], "test@example.com")
        self.assertEqual(config["password"], "primary-password")

    def test_toggle_on_custom_username_overrides_login(self):
        """When custom_outgoing_server_username is set, login uses that value instead of the standard login_id."""
        account = _build_account(
            custom_use_separate_credential_for_outgoing=1,
            custom_outgoing_server_username="alice-outgoing",
        )

        config = account.sendmail_config()

        self.assertEqual(config["login"], "alice-outgoing")

    def test_toggle_on_custom_password_fetched_from_encrypted_field(self):
        """When custom_outgoing_server_password is set, password is fetched via get_password from that field."""
        account = _build_account(
            custom_use_separate_credential_for_outgoing=1,
            custom_outgoing_server_password="set",
        )

        with patch.object(account, "get_password", return_value="custom-secret") as mock_get:
            config = account.sendmail_config()

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs["fieldname"], "custom_outgoing_server_password")
        self.assertEqual(config["password"], "custom-secret")

    def test_password_fetch_uses_raise_false_in_test_mode(self):
        """In test mode (frappe.flags.in_test=True), get_password is called with raise_exception=False."""
        account = _build_account(
            custom_use_separate_credential_for_outgoing=1,
            custom_outgoing_server_password="set",
        )

        with patch.object(account, "get_password", return_value="x") as mock_get:
            account.sendmail_config()

        self.assertEqual(mock_get.call_args.kwargs["raise_exception"], False)

    def test_password_fetch_uses_raise_false_when_no_smtp_authentication(self):
        """When no_smtp_authentication=1, get_password is called with raise_exception=False even outside test mode."""
        account = _build_account(
            custom_use_separate_credential_for_outgoing=1,
            custom_outgoing_server_password="set",
            no_smtp_authentication=1,
        )

        original_in_test = frappe.flags.in_test
        frappe.flags.in_test = False
        try:
            with patch.object(account, "get_password", return_value="x") as mock_get:
                account.sendmail_config()
        finally:
            frappe.flags.in_test = original_in_test

        self.assertEqual(mock_get.call_args.kwargs["raise_exception"], False)

    def test_password_fetch_uses_raise_true_in_production(self):
        """Outside test mode and with SMTP auth required, raise_exception is True so a missing custom password would raise."""
        account = _build_account(
            custom_use_separate_credential_for_outgoing=1,
            custom_outgoing_server_password="set",
            no_smtp_authentication=0,
        )

        original_in_test = frappe.flags.in_test
        frappe.flags.in_test = False
        try:
            with patch.object(account, "get_password", return_value="x") as mock_get:
                account.sendmail_config()
        finally:
            frappe.flags.in_test = original_in_test

        self.assertEqual(mock_get.call_args.kwargs["raise_exception"], True)


class TestSendmailConfigShape(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        password_patcher = patch.object(
            EmailAccount, "_password", new_callable=PropertyMock, return_value="primary-password"
        )
        password_patcher.start()
        self.addCleanup(password_patcher.stop)

    def test_config_has_required_keys(self):
        """Returned dict contains every key SMTP callers expect."""
        account = _build_account(custom_use_separate_credential_for_outgoing=1)

        config = account.sendmail_config()

        required = {
            "email_account",
            "server",
            "port",
            "login",
            "password",
            "use_ssl",
            "use_tls",
            "use_oauth",
            "access_token",
        }
        self.assertTrue(required.issubset(set(config.keys())))

    def test_use_oauth_false_and_access_token_none(self):
        """The override path never enables OAuth: use_oauth is False, access_token is None."""
        account = _build_account(custom_use_separate_credential_for_outgoing=1)

        config = account.sendmail_config()

        self.assertEqual(config["use_oauth"], False)
        self.assertIsNone(config["access_token"])

    def test_validate_smtp_connection_flag_adds_timeout(self):
        """When account.flags.validate_smtp_connection is set, the returned config includes timeout=15."""
        account = _build_account(custom_use_separate_credential_for_outgoing=1)
        account.flags.validate_smtp_connection = True

        config = account.sendmail_config()

        self.assertEqual(config["timeout"], 15)
