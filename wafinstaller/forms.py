from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm, UserCreationForm

class AdminLogin(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control mb-0', 'placeholder': 'Enter your username'
        }),
        label='Username'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control mb-0', 'placeholder': 'Enter your password'
        }),
        label='Password'
    )

class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class AdminPasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(AdminPasswordForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'




# -------------------------
# Users management
# -------------------------

class _BootstrapFormMixin:
    """Apply bootstrap classes to every widget."""

    def _apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class UserCreateForm(_BootstrapFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["is_active"].initial = True
        self._apply_bootstrap()


class UserEditForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self._apply_bootstrap()


class UserSetPasswordForm(_BootstrapFormMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


# -------------------------
# Syslog
# -------------------------

class SyslogConfigForm(_BootstrapFormMixin, forms.Form):
    enabled = forms.BooleanField(required=False, label="Enable syslog forwarding")
    host = forms.CharField(required=False, max_length=255, label="Syslog server",
                           help_text="Hostname or IP address of the syslog / SIEM server.")
    port = forms.IntegerField(min_value=1, max_value=65535, initial=514, label="Port")
    protocol = forms.ChoiceField(choices=[("udp", "UDP"), ("tcp", "TCP")], label="Protocol")
    facility = forms.ChoiceField(label="Facility")
    format = forms.ChoiceField(choices=[("rfc5424", "RFC 5424"), ("rfc3164", "RFC 3164 (BSD)")],
                               label="Message format")
    app_name = forms.CharField(max_length=48, initial="wafcontrol", label="App name / tag",
                               validators=[RegexValidator(r"^[A-Za-z0-9._-]+$",
                                                          "Use letters, digits, '.', '_' or '-'.")])
    send_attacks = forms.BooleanField(required=False, label="Send WAF attacks")
    send_audit = forms.BooleanField(required=False, label="Send user actions (audit log)")

    def __init__(self, *args, **kwargs):
        from wafinstaller.helper.syslog import FACILITIES
        super().__init__(*args, **kwargs)
        self.fields["facility"].choices = [(f, f) for f in FACILITIES]
        self._apply_bootstrap()

    def clean(self):
        data = super().clean()
        if data.get("enabled") and not (data.get("host") or "").strip():
            self.add_error("host", "Required when syslog is enabled.")
        data["host"] = (data.get("host") or "").strip()
        return data
