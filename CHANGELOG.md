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
- **Geo Lists**: allow/deny lists by country (plus optional extra IPs), built from the bundled GeoLite2-Country database.
  nginx uses its built-in `geo` module (`$wafc_geo_<name>` variable, fast even for large countries); Apache gets the
  countries expanded into `Require ip` ranges. A "Refresh Geo Lists" button re-generates them after a GeoIP update.

### Fixed
- App signals were never connected (`WafinstallerConfig.ready()` was defined outside the class).

### Upgrade notes
A database update is required (IP Lists / Geo Lists). After updating the code:

```bash
python manage.py makemigrations wafinstaller
python manage.py migrate
```

Then restart the panel and Celery services.

## v1.0.0
- Initial release.
