from wafinstaller.helper.nginx_conf import NginxConfManager


def nginx_state(request):
    """Expose whether nginx is installed so the sidebar can show the conf.d page."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    return {"nginx_installed": NginxConfManager.is_nginx_installed()}
