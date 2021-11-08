#!/usr/bin/env python
import sys
from datetime import datetime

from tinydb import TinyDB, where
from jira import JIRA, resources

from django import forms
from django.conf import settings
from django.conf.urls.static import static
from django.core import wsgi, management, cache
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path, reverse_lazy
from django.shortcuts import render


db = TinyDB("db.json", sort_keys=True, indent=2, separators=(",", ": "))
credentials_tbl = db.table("credentials")


if not settings.configured:
    settings.configure(
        DEBUG=True,
        MIDDLEWARE=["server.credentials_middleware"],
        INSTALLED_APPS=["django.contrib.staticfiles"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": ["src/templates"],
            }
        ],
        STATIC_URL="/static/",
        STATICFILES_DIRS=["src/static"],
        STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
        ROOT_URLCONF="server",
        SECRET_KEY="selfiesecret",
    )


def credentials_middleware(get_response):
    def middleware(request: HttpRequest):
        table = db.table("credentials")
        if not table.all() and not request.path.endswith("login"):
            return HttpResponseRedirect(reverse_lazy("login"))
        return get_response(request)

    return middleware


class LoginForm(forms.Form):
    jira_instance = forms.URLField()
    jira_email = forms.EmailField()
    jira_token = forms.CharField()


def login_view(request: HttpRequest):
    table = db.table("credentials")
    form = LoginForm()
    if request.POST:
        form = LoginForm(request.POST)
        if form.is_valid():
            table.insert(form.cleaned_data)
            return HttpResponseRedirect(reverse_lazy("timer"))
    return render(request, "login.html", {"form": form})


empty_timer = {
    "project": None,
    "task": None,
    "start": None,
    "end": None,
    "elapsed": None,
}


def stopwatch(request: HttpRequest):
    table = db.table("records")
    timer = {**empty_timer}
    # Searching only in unfinished records
    timers = table.search(~where("end").exists())
    if timers:
        timer = timers[0]
    if request.method == "POST":
        if timer:
            table.update(
                {"end": datetime.now().strftime("%Y-%M-%d %H:%m:%S")},
                doc_ids=[timer.doc_id],
            )
        if "close" in request.POST:
            timer = {**empty_timer}
        else:
            timer["project"] = request.POST["project"]
            timer["task"] = db.table("project_settings").get(
                where("project") == timer["project"]
            )["task"]
            timer["start"] = datetime.now().strftime("%Y-%M-%d %H:%m:%S")
            table.insert(timer)
    if timer["start"]:
        timer["elapsed"] = str(
            datetime.now() - datetime.strptime(timer["start"], "%Y-%M-%d %H:%m:%S")
        ).split(".")[0]
    return render(
        request,
        "timer.html",
        {
            "tabs": ["log", "report", "settings"],
            "selected_tab": "log",
            "projects": db.table("project_settings").all(),
            "timer": timer,
        },
    )


def report_view(request: HttpRequest):
    table = db.table("records")
    records = table.all()
    return render(
        request,
        "report.html",
        {
            "tabs": ["log", "report", "settings"],
            "selected_tab": "report",
            "rows": records,
        },
    )


def get_jira_client():
    credentials = credentials_tbl.all()[0]
    return JIRA(
        credentials["jira_instance"],
        basic_auth=(credentials["jira_email"], credentials["jira_token"]),
        options={"agile_rest_path": resources.GreenHopperResource.AGILE_BASE_REST_PATH},
    )


class ProjectForm(forms.Form):
    project = forms.CharField()
    task = forms.CharField()


def settings_view(request: HttpRequest):
    projects = cache.cache.get("projects")
    tasks = cache.cache.get("timetracking_tasks")
    if projects is None:
        client = get_jira_client()
        projects = {p.key: p.name for p in client.projects()}
        tasks = {
            i.key: {"summary": i.fields.summary}
            for i in client.search_issues(
                "issuetype = Time-Tracking", fields="summary", maxResults=False
            )
        }
        cache.cache.set("projects", projects)
        cache.cache.set("timetracking_tasks", tasks)
    ProjectFormFormSet = forms.formset_factory(ProjectForm, extra=8, max_num=8)
    formset = ProjectFormFormSet(initial=db.table("project_settings").all())
    if request.method == "POST":
        formset = ProjectFormFormSet(
            request.POST, initial=db.table("project_settings").all()
        )
        if formset.is_valid():
            db.drop_table("project_settings")
            db.table("project_settings").insert_multiple(
                [fdata for fdata in formset.cleaned_data if fdata]
            )
    return render(
        request,
        "settings.html",
        {
            "tabs": ["log", "report", "settings"],
            "selected_tab": "settings",
            "projects": projects,
            "tasks": tasks,
            "formset": formset,
        },
    )


urlpatterns = [
    path("", stopwatch, name="log"),
    path("login", login_view, name="login"),
    path("settings", settings_view, name="settings"),
    path("report", report_view, name="report"),
] + static(settings.STATIC_URL)

app = wsgi.get_wsgi_application()

if __name__ == "__main__":
    management.execute_from_command_line(sys.argv)
