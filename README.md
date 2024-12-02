# Frappe Email Send Override

The app enhances the Frappe framework's Email Account functionality by enabling the configuration of different credentials for outgoing and incoming mail servers within the same email account. This feature is particularly useful when the SMTP server and the incoming mail server require separate authentication details.

## Installation

1. Get the app

```bash
bench get-app https://github.com/rtCamp/frappe-email-send-override.git
```

2. Install the app on your site

```bash
bench --site [site-name] install-app email_send_override
```

#### Setup App on Frappe Site

Please refer to the [wiki](https://github.com/rtCamp/frappe-email-send-override/wiki) for setting up and using the app in Frappe site.


## Contribution Guide

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## License

This project is licensed under the [AGPLv3 License](./LICENSE).
