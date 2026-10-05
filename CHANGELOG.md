# Changelog

## v1.1.0

### Added
- **Nginx Config**: list, view, create and edit `/etc/nginx/conf.d/*.conf` from the panel (shown when nginx is installed).
- **Apache Config**: same for Apache (`/etc/apache2/sites-available` on Debian/Ubuntu with enable on create, `/etc/httpd/conf.d` on RHEL).
  Every change is validated with the server config test and rolled back on failure, then the server is reloaded.
- **Users Management**: list, create, edit, enable/disable and delete panel administrators, set passwords and reset 2FA.
  An admin cannot delete or disable their own account, and the last active admin is protected.
- **Syslog Config**: forward WAF attacks and user actions (audit log, login/logout, failed login/2FA) to a syslog / SIEM
  server over UDP or TCP, RFC 5424 or RFC 3164, with enable/disable, per-event toggles and a test message.
  Passwords, OTP codes and file contents are never sent.
- **IP Lists**: named allow/deny lists of IPv4/IPv6 addresses and CIDR ranges, published as include files for nginx
  (`/etc/nginx/wafcontrol/iplists/`) and Apache (`/etc/apache2/wafcontrol/iplists/`), with a usage guide for each server.

### Fixed
- App signals were never connected (`WafinstallerConfig.ready()` was defined outside the class).

### Upgrade notes
A new database table is required (IP Lists). After updating the code:

```bash
python manage.py makemigrations wafinstaller
python manage.py migrate
```

Then restart the panel and Celery services.

## v1.0.0
- Initial release.
